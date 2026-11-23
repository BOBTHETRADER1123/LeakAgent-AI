import os
import csv
import io
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from library import ROOT, Library, get_embedder, seed
from llm import answer
from evaluate import metrics
from battledim_importer import parse_wide_csv, compare_sensor_baselines, extract_reference_leak_events

load_dotenv(ROOT/'.env')
st.set_page_config(page_title='LeakLogic AI 4.7',page_icon='💧',layout='wide')
st.title('LeakLogic AI 4.7')
st.caption('India-first possible water leakage detection • hydraulic screening • local RAG research assistant')

@st.cache_resource
def embeddings():
    return get_embedder()

with st.sidebar:
    page=st.radio('Workspace',['Whole-pipeline mapping','Leakage detection','Research assistant','Document library','Indian datasets','BattLeDIM benchmark','Hydraulic diagnosis','Evaluation'])
    key=st.text_input('OpenRouter API key',value=os.getenv('OPENROUTER_API_KEY',''),type='password')
    model=st.text_input('LLM model ID',value=os.getenv('OPENROUTER_MODEL','openrouter/free'))
    consent=st.checkbox('Allow sending my question and retrieved excerpts to OpenRouter and its provider.')
    st.caption('Embeddings and SQLite stay on your laptop. Cloud model availability and charges depend on model and provider. Use only authorized data.')

if page=='Whole-pipeline mapping':
    st.subheader('Whole-pipeline spatial leakage screening')
    st.write('Map measurements from monitoring stations along the complete pipeline. The system analyzes each interval between adjacent stations and records chainage in millimetres.')
    st.warning('Important: millimetre coordinate storage is not 1 mm physical detection accuracy. With flow-balance data, a possible leak is bracketed between adjacent monitoring stations. Add stations or validated distributed sensing to improve localization.')
    pipe_length = st.number_input('Total pipeline length (metres)', min_value=1.0, max_value=10000000.0, value=200000.0, step=1000.0)
    template=ROOT/'templates/spatial_pipeline_readings.csv'
    st.download_button('Download whole-pipeline CSV template',template.read_bytes(),template.name,'text/csv')
    upload=st.file_uploader('Upload monitoring-station readings CSV',type='csv',key='spatial_csv')
    if st.button('Analyze entire pipeline',type='primary') and upload:
        try:
            rows=list(csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig'))))
            response=requests.post('http://127.0.0.1:8000/spatial-detect',json={'rows':rows,'pipe_length_m':pipe_length},timeout=120)
            if not response.ok:
                st.error(f'Backend returned {response.status_code}: {response.text[:2000]}')
            else:
                report=response.json()
                st.success(report['status'])
                c1,c2,c3=st.columns(3)
                c1.metric('Pipeline length',f"{report['pipe_length_m']:,.0f} m")
                c2.metric('Intervals analyzed',report['intervals_analyzed'])
                c3.metric('Possible leak intervals',report['possible_leak_intervals'])
                st.subheader('Possible leak location intervals')
                st.dataframe(report['location_summary'],use_container_width=True)
                st.subheader('Every adjacent-station interval analyzed')
                st.dataframe(report['interval_results'],use_container_width=True)
                st.info('For a 200 km pipeline, the coordinate reference can represent 200,000,000,000 millimetre positions without creating 200 billion database rows. The actual location uncertainty is the distance between the stations that bracket the anomaly.')
                for item in report['limitations']: st.caption('• '+item)
                st.download_button('Download full spatial report',json.dumps(report,indent=2),'whole_pipeline_spatial_report.json','application/json')
        except requests.RequestException:
            st.error('Start FastAPI in another terminal first. See README startup instructions.')
        except Exception as e: st.error(str(e))
    st.subheader('Required monitoring data')
    st.markdown('Each station needs a synchronized timestamp, chainage distance from the pipe start, measured flow, meter uncertainty, known withdrawal between stations, and stable/full-pipe verification. Pressure readings can be added in a later calibrated localization module.')
elif page=='Leakage detection':
    st.subheader('Possible leakage screening')
    st.write('Upload paired inlet/outlet readings for each pipeline segment and supply cycle. The detector looks for unexplained positive flow imbalance relative to stated meter uncertainty.')
    st.warning('Use only stable, full-pipe windows. Account for all branch taps and pipe storage changes. A flag means possible leakage, not confirmed leakage.')
    template=ROOT/'templates/leak_detection_readings.csv'
    st.download_button('Download CSV template',template.read_bytes(),template.name,'text/csv')
    upload=st.file_uploader('Upload pipeline measurements CSV',type='csv',key='leak_csv')
    if st.button('Analyze for possible leakage',type='primary') and upload:
        try:
            rows=list(csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig'))))
            response=requests.post('http://127.0.0.1:8000/detect',json={'rows':rows},timeout=60)
            if not response.ok:
                st.error(f'Backend returned {response.status_code}: {response.text[:2000]}')
            else:
                report=response.json()
                status=report['overall_status']
                if status=='POSSIBLE LEAK SIGNAL FOUND': st.error(status)
                elif status=='ANOMALY NEEDS RECHECK': st.warning(status)
                else: st.success(status)

                st.subheader('Pipeline diagnostic')
                if report.get('row_results'):
                    row_options = {
                        f"Row {r['csv_row']} • {r['branch_id']} • Cycle {r['cycle_id']}": r
                        for r in report['row_results']
                    }
                    selected_label = st.selectbox('Measurement to display', list(row_options))
                    selected = row_options[selected_label]
                    duration_min = st.number_input(
                        'Estimate potential loss over (minutes)', min_value=1, max_value=10080,
                        value=100, step=5, key='diagnostic_duration')
                    q_in = float(selected['q_up_l_s'])
                    q_out = float(selected['q_down_l_s'])
                    raw_difference = q_in - q_out
                    # The card's volume is a gross inlet/outlet imbalance estimate.
                    # Known taps/storage are shown separately so this is not mislabelled as confirmed leakage.
                    potential_loss = max(0.0, raw_difference) * 60.0 * float(duration_min)
                    branch = next((b for b in report.get('branches', [])
                                   if b['branch_id'] == selected['branch_id']), {})
                    branch_status = branch.get('status', 'INSUFFICIENT EVIDENCE')
                    if 'POSSIBLE LEAK' in branch_status:
                        badge_text = 'Possible leakage'
                    elif 'ANOMALY' in branch_status or selected.get('possible_leak_signal'):
                        badge_text = 'Anomaly — recheck'
                    else:
                        badge_text = 'No qualifying leak signal'
                    evidence = [
                        f"Inlet and outlet flows differ by {raw_difference:,.3f} L/s.",
                        f"Unexplained residual after entered storage/tap adjustments: {selected['unexplained_flow_l_s']:,.3f} L/s.",
                        f"Combined meter uncertainty: {selected['combined_meter_sigma_l_s']:,.3f} L/s; screening z-score: {selected['z_score']}.",
                        "Stable, full-pipe verification: " + ("passed" if selected['eligible'] else "not satisfied") + ".",
                    ]
                    if 'POSSIBLE LEAK' in branch_status:
                        evidence.append("The branch-level screening threshold was exceeded in at least two distinct verified cycles.")
                    elif 'ANOMALY' in branch_status:
                        evidence.append("Only one distinct flagged cycle is present; repeat measurements before escalation.")
                    else:
                        evidence.append("The available row/branch evidence does not meet the repeated-cycle possible-leak rule.")
                    badge_bg = '#fce7dc' if 'Possible' in badge_text else ('#fff1d6' if 'Anomaly' in badge_text else '#e7f3ea')
                    badge_fg = '#9a3412' if 'Possible' in badge_text else ('#92400e' if 'Anomaly' in badge_text else '#166534')
                    evidence_html = ''.join(f'<li>{item}</li>' for item in evidence)
                    st.markdown(f'''
                    <div style="border:1px solid #dedede;border-radius:16px;padding:18px 20px;margin:8px 0 18px 0;background:var(--secondary-background-color,#fff);">
                      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
                        <div style="font-size:20px;font-weight:650;">Pipeline diagnostic</div>
                        <span style="background:{badge_bg};color:{badge_fg};padding:5px 11px;border-radius:18px;font-size:14px;">{badge_text}</span>
                      </div>
                      <div style="display:grid;grid-template-columns:1fr 1fr;gap:22px 28px;margin-top:18px;">
                        <div><div style="color:gray;">Inlet flow</div><div style="font-size:30px;font-weight:600;">{q_in:,.3g}</div><div style="color:gray;">Litres/second</div></div>
                        <div><div style="color:gray;">Outlet flow</div><div style="font-size:30px;font-weight:600;">{q_out:,.3g}</div><div style="color:gray;">Litres/second</div></div>
                        <div><div style="color:gray;">Flow difference</div><div style="font-size:29px;font-weight:600;color:#a34112;">{raw_difference:,.3g}</div><div style="color:gray;">Litres/second</div></div>
                        <div><div style="color:gray;">Potential loss</div><div style="font-size:29px;font-weight:600;">{potential_loss:,.0f}</div><div style="color:gray;">Litres over {duration_min:,.0f} minutes, if sustained</div></div>
                      </div>
                      <hr style="border:0;border-top:1px solid #e5e5e5;margin:18px 0;">
                      <div style="font-size:18px;font-weight:650;margin-bottom:8px;">Diagnostic evidence</div>
                      <ul style="padding-left:22px;margin-bottom:16px;">{evidence_html}</ul>
                      <div style="font-size:13px;color:gray;">Indicative screening result only. Gross flow difference is not necessarily leakage; unmeasured demand, storage changes, meter error and operating conditions can affect it. Not a confirmed leak.</div>
                    </div>
                    ''', unsafe_allow_html=True)
                    st.download_button('Download this pipeline diagnostic',
                        json.dumps({'selected_measurement': selected, 'branch_summary': branch,
                                    'duration_minutes': duration_min,
                                    'gross_imbalance_litres_if_sustained': potential_loss,
                                    'status_label': badge_text}, indent=2),
                        'pipeline_diagnostic.json', 'application/json')
                c1,c2,c3=st.columns(3)
                c1.metric('Rows analyzed',report['rows_analyzed'])
                c2.metric('Eligible stable windows',report['eligible_rows'])
                c3.metric('Branches checked',len(report['branches']))
                st.subheader('Pipeline segment results')
                st.dataframe(report['branches'],use_container_width=True)
                st.subheader('Individual measurement results')
                st.dataframe(report['row_results'],use_container_width=True)
                st.subheader('What this result means')
                for item in report['limitations']: st.caption('• '+item)
                st.download_button('Download full leakage screening report',json.dumps(report,indent=2),'leakage_screening_report.json','application/json')
        except requests.RequestException:
            st.error('Start FastAPI in another terminal first. See README startup instructions.')
        except Exception as e: st.error(str(e))
    st.subheader('How the screening rule works')
    st.latex(r'R = Q_{in} - Q_{out} - Q_{storage} - Q_{known\\ taps}')
    st.latex(r'\\sigma_R = \\sqrt{\\sigma_{in}^2+\\sigma_{out}^2}')
    st.latex(r'\\text{Possible signal if } R > 3\\sigma_R')
    st.caption('A branch is escalated to POSSIBLE LEAK when the threshold is exceeded in at least two distinct verified cycles. This is a conservative prototype rule, not a calibrated probability.')
elif page=='Document library':
    st.info('Index bundled project documents and Indian measurements, then add your authorized searchable PDFs. No cloud key required for indexing.')
    if st.button('Index bundled knowledge base'):
        try:
            with st.spinner('Building local SQLite embedding index'):
                count=seed(Library(embeddings()))
            st.success(f'{count} new chunks indexed.')
        except Exception as e: st.error(str(e))
    upload=st.file_uploader('Add authorized PDF',type='pdf')
    if st.button('Index uploaded PDF') and upload:
        try:
            count,skipped=Library(embeddings()).add_pdf(upload.getvalue(),upload.name)
            st.success(f'{count} new chunks. Skipped textless pages: {skipped or "none"}')
        except Exception as e: st.error(str(e))
    st.dataframe([{'source':a,'type':b,'chunks':c} for a,b,c in Library().sources()],use_container_width=True)
elif page=='Research assistant':
    st.info('Ask about the project equations, Indian data and methodology. The Leakage detection workspace performs measurement-based screening; RAG only retrieves supporting documents.')
    if not Library().sources(): st.warning('Use Document library → Index bundled knowledge base first, or run ingest.py.')
    use_llm=st.checkbox('Generate an LLM answer (optional)')
    if 'history' not in st.session_state: st.session_state.history=[]
    for turn in st.session_state.history:
        with st.chat_message('user'): st.write(turn['question'])
        with st.chat_message('assistant'):
            st.write(turn['answer'])
            if turn['invalid']: st.warning('Invalid source labels: '+str(turn['invalid']))
            with st.expander('Retrieved evidence'):
                for i,r in enumerate(turn['sources'],1):
                    st.markdown(f'**[S{i}] {r["title"]} — {r["location"]}**')
                    st.caption(r['kind']+' | cosine similarity '+str(round(r['score'],3))+' (not confidence)')
                    st.text(r['text'])
                    if r['url']: st.write(r['url'])
    if question:=st.chat_input('Ask about LeakLogic or the Indian datasets'):
        try:
            if use_llm and not consent: raise ValueError('Enable cloud consent before sending data.')
            with st.spinner('Retrieving sources'):
                sources=Library(embeddings()).search(question)
                text,invalid=answer(question,sources,key,model) if use_llm else ('Local retrieval only. See the ranked evidence below; no LLM answer generated.',[])
            st.session_state.history.append(dict(question=question,answer=text,invalid=invalid,sources=sources))
            st.rerun()
        except Exception as e: st.error(str(e))
elif page=='Indian datasets':
    st.warning('Nagpur measurements are published field observations, not paired branch readings or verified leak episodes. They cannot establish a leak win rate.')
    st.dataframe(list(csv.DictReader(io.StringIO((ROOT/'datasets/nagpur/measurements_si.csv').read_text()))),use_container_width=True)
    st.subheader('Source manifest')
    st.dataframe(list(csv.DictReader(io.StringIO((ROOT/'sources.csv').read_text()))),use_container_width=True)
    st.markdown('Run `download_originals.py` to fetch the IIT Bombay and Delhi–Bengaluru archives directly from their publishers. Extract and inspect them separately; they are not labelled leak datasets.')
    st.download_button('Download included Nagpur CSV',(ROOT/'datasets/nagpur/measurements_si.csv').read_bytes(),'nagpur_measurements.csv','text/csv')
elif page=='BattLeDIM benchmark':
    st.subheader('BattLeDIM SCADA benchmark importer')
    st.warning('BattLeDIM is an international L-Town benchmark. The SCADA files are 5-minute time series; the network and evaluation data are benchmark/simulation-derived, not Indian HMWSSB measurements. Statistical anomalies are not confirmed leaks.')
    st.markdown('Upload the original CSVs downloaded from the official Zenodo record. Use matching data types for each year. Recommended: 2018 pressure + flow as historical reference, and 2019 pressure + flow as evaluation data. Upload leakage time-series separately; this page will preserve them as reference data and will not pretend they are sensor readings.')
    st.markdown('[Official BattLeDIM Zenodo dataset](https://zenodo.org/records/4017659) · [Official data description and sensor units](https://battledim.ucy.ac.cy/?page_id=33)')
    st.caption('Expected files: 2018_SCADA_Pressures.csv, 2018_SCADA_Flows.csv, 2019_SCADA_Pressures.csv, 2019_SCADA_Flows.csv. Optional: 2018_Leakages.csv and 2019_Leakages.csv.')
    c1,c2=st.columns(2)
    with c1:
        p18=st.file_uploader('2018 pressure CSV (m)',type='csv',key='bd_p18')
        f18=st.file_uploader('2018 flow CSV (m³/h)',type='csv',key='bd_f18')
        l18=st.file_uploader('2018 leakage reference CSV (m³/h)',type='csv',key='bd_l18')
    with c2:
        p19=st.file_uploader('2019 pressure CSV (m)',type='csv',key='bd_p19')
        f19=st.file_uploader('2019 flow CSV (m³/h)',type='csv',key='bd_f19')
        l19=st.file_uploader('2019 leakage reference CSV (m³/h)',type='csv',key='bd_l19')
    if st.button('Import and compare BattLeDIM files',type='primary'):
        try:
            training=[]; evaluation=[]; summaries=[]; leak_refs=[]
            for upload,kind,year,target in [
                (p18,'pressure','2018',training),(f18,'flow','2018',training),
                (p19,'pressure','2019',evaluation),(f19,'flow','2019',evaluation)]:
                if upload:
                    result=parse_wide_csv(upload.getvalue(),upload.name,kind,year)
                    target.extend(result['records'])
                    summaries.append({'file':upload.name,'year':year,'type':kind,'timestamps':result['row_count'],'sensors':result['sensor_count'],'observations':len(result['records']),'first':result['first_timestamp'],'last':result['last_timestamp'],'skipped':result['skipped_values']})
            for upload,year in [(l18,'2018'),(l19,'2019')]:
                if upload:
                    result=parse_wide_csv(upload.getvalue(),upload.name,'leakage_reference',year)
                    leak_refs.extend(result['records'])
                    summaries.append({'file':upload.name,'year':year,'type':'leakage reference (separate)','timestamps':result['row_count'],'sensors':result['sensor_count'],'observations':len(result['records']),'first':result['first_timestamp'],'last':result['last_timestamp'],'skipped':result['skipped_values']})
            if not training and not evaluation and not leak_refs:
                raise ValueError('Upload at least one original BattLeDIM CSV file.')
            st.success('BattLeDIM CSV import completed.')
            st.dataframe(summaries,use_container_width=True)
            # Keep parsed data in this browser session so the event explorer remains
            # available after Streamlit reruns and does not require re-uploading.
            st.session_state['bd_training'] = training
            st.session_state['bd_evaluation'] = evaluation
            st.session_state['bd_leak_refs'] = leak_refs
            if training and evaluation:
                anomalies=compare_sensor_baselines(training,evaluation)
                st.subheader('2019 deviations from 2018 sensor baselines')
                st.caption('Per-sensor absolute z-score ≥ 3 using the 2018 median and population standard deviation. This is a simple screening baseline, not a validated BattLeDIM competition detector or a leak confirmation.')
                st.metric('Statistical anomalies',len(anomalies))
                if anomalies: st.dataframe(anomalies[:500],use_container_width=True)
                else: st.info('No sensor deviations crossed the screening threshold, or no matching sensor had a usable historical standard deviation.')
                st.download_button('Download anomaly screening JSON',data=__import__('json').dumps(anomalies,indent=2),file_name='battledim_anomaly_screening.json',mime='application/json')
            all_records=training+evaluation+leak_refs
            st.subheader('Imported observation preview')
            st.dataframe(all_records[:100],use_container_width=True)
            csv_buffer=io.StringIO(); writer=csv.DictWriter(csv_buffer,fieldnames=['dataset','year','kind','timestamp','sensor_id','value','source_file']); writer.writeheader(); writer.writerows(all_records)
            st.download_button('Download normalized BattLeDIM observations CSV',csv_buffer.getvalue(),'battledim_normalized_observations.csv','text/csv')
            st.info('Pressure units: metres of head. Flow and leakage units: m³/h. Demand data, if uploaded separately, is L/h. Sensor IDs identify L-Town network nodes/links. This importer does not convert these sensors into a serial pipeline station chainage; use the network model for topology-aware localization.')
        except Exception as e:
            st.error(str(e))

    # Reference-event explorer: displays periods encoded by positive leakage outflow.
    saved_leaks = st.session_state.get('bd_leak_refs', [])
    if saved_leaks:
        st.divider()
        st.header('Leakage reference explorer')
        st.caption('These are reference leakage periods parsed from BattLeDIM leak-outflow series, not detections made by LeakLogic. Positive reference outflow is grouped into continuous five-minute periods per pipe ID.')
        events = extract_reference_leak_events(saved_leaks)
        if events:
            import pandas as pd
            event_df = pd.DataFrame(events)
            a,b,c,d = st.columns(4)
            a.metric('Reference periods', len(events))
            b.metric('Affected pipe IDs', event_df['pipe_id'].nunique())
            c.metric('2018 periods', int((event_df['year']=='2018').sum()))
            d.metric('2019 periods', int((event_df['year']=='2019').sum()))
            st.subheader('Reference leakage periods')
            st.dataframe(event_df, use_container_width=True, hide_index=True)
            st.download_button('Download extracted reference leakage events', event_df.to_csv(index=False), 'battledim_reference_leak_events.csv', 'text/csv')
            st.subheader('Inspect a reference pipe')
            available = sorted({(str(r['year']), str(r['sensor_id'])) for r in saved_leaks})
            chosen = st.selectbox('Year and pipe ID', available, format_func=lambda x: f'{x[0]} — {x[1]}')
            pipe_rows = [r for r in saved_leaks if str(r['year']) == chosen[0] and str(r['sensor_id']) == chosen[1]]
            plot_df = pd.DataFrame([{'timestamp': pd.to_datetime(r['timestamp']), 'leak_outflow_m3_h': float(r['value'])} for r in pipe_rows]).set_index('timestamp').sort_index()
            st.line_chart(plot_df)
            st.caption('The approximate volume column integrates the supplied five-minute outflow samples. It is an estimate from the benchmark reference series, not a field-measured volume report.')
        else:
            st.warning('Leakage-reference files were imported, but no positive outflow intervals were found. Check that the correct leakage CSVs were uploaded.')
elif page=='Hydraulic diagnosis':
    st.info('Upload one independently verified stable, full-pipe window per branch and supply cycle. Do not assign missing fields from guesses. Output is preliminary screening only.')
    template=ROOT/'templates/stable_cycle_readings.csv'
    st.download_button('Download stable-cycle CSV template',template.read_bytes(),template.name,'text/csv')
    upload=st.file_uploader('Stable-cycle measurements',type='csv')
    if st.button('Run four agents') and upload:
        try:
            rows=list(csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig'))))
            response=requests.post('http://127.0.0.1:8000/diagnose',json={'readings':rows},timeout=60)
            if not response.ok: st.error(f'Backend returned {response.status_code}'); st.code(response.text[:3000])
            else:
                report=response.json(); st.json(report)
                st.download_button('Download diagnostic report',json.dumps(report,indent=2),'diagnosis.json','application/json')
        except requests.RequestException: st.error('Start FastAPI in another terminal (see README).')
        except Exception as e: st.error(str(e))
else:
    st.subheader('Independent held-out evaluation')
    st.warning('Accuracy unknown until verified actual leak / normal labels AND independently generated predictions are supplied. Never use the predictions as ground truth.')
    template=ROOT/'templates/evaluation_predictions.csv'
    st.download_button('Download evaluation template',template.read_bytes(),template.name,'text/csv')
    upload=st.file_uploader('Held-out case labels and predictions',type='csv')
    confirmed=st.checkbox('These are independently verified labels on held-out cases, not model-created labels.')
    if st.button('Calculate metrics') and upload:
        try:
            if not confirmed: raise ValueError('Verify the label provenance first.')
            st.json(metrics(list(csv.DictReader(io.StringIO(upload.getvalue().decode('utf-8-sig'))))))
        except Exception as e: st.error(str(e))
