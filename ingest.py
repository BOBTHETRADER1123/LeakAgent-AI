from library import Library, get_embedder, seed

if __name__ == '__main__':
    print('Loading local Hugging Face embeddings (internet needed on first run).')
    library = Library(get_embedder())
    print('New chunks:', seed(library))
    print('Indexed sources:', library.sources())
