"""Only score externally labelled, independently verified evaluation cases."""
import csv
import argparse


def metrics(rows):
    if not rows:
        raise ValueError('No labelled held-out predictions. Actual performance unknown.')
    seen=set(); tp=tn=fp=fn=abstain=0
    for r in rows:
        case=r['case_id'].strip(); actual=r['actual'].strip(); pred=r['prediction'].strip()
        if not case or case in seen or actual not in ('leak','normal') or pred not in ('leak','normal','unresolved'):
            raise ValueError('Need unique case IDs, verified actual leak/normal and valid predictions.')
        seen.add(case)
        if pred=='unresolved': abstain+=1
        if actual=='leak':
            if pred=='leak': tp+=1
            else: fn+=1
        elif pred=='leak': fp+=1
        elif pred=='normal': tn+=1
    def ratio(a,b): return round(100*a/b,2) if b else None
    # Unresolved normal cases do not count as true negatives; they remain in total normal cases.
    normal=sum(r['actual'].strip()=='normal' for r in rows)
    return {'cases':len(rows),'TP':tp,'TN':tn,'FP':fp,'FN_including_unresolved_leaks':fn,'unresolved':abstain,'accuracy_pct':ratio(tp+tn,len(rows)),'recall_pct':ratio(tp,tp+fn),'precision_pct':ratio(tp,tp+fp),'false_alarm_pct':ratio(fp,normal),'f1_pct':ratio(2*tp,2*tp+fp+fn),'coverage_pct':ratio(len(rows)-abstain,len(rows))}

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('csv'); args=p.parse_args()
    with open(args.csv,newline='',encoding='utf-8-sig') as f:
        print(metrics(list(csv.DictReader(f))))
