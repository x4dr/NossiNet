import os

import numpy as np
import ollama


def embed_text(texts):
    embeddings = []
    for i, text in enumerate(texts):
        print(f"Embedding text {i+1}/{len(texts)} (length: {len(text)})...")
        response = ollama.embeddings(model="nomic-embed-text", prompt=text)
        emb = response["embedding"]
        print(f"Embedding vector (first 5 values): {emb[:5]}")
        embeddings.append(np.array(emb))
    return embeddings


def get_top_k(query, embeddings, texts, filenames, k=3, window=30):
    print(f"Embedding query: {query}")
    q_emb = ollama.embeddings(model="nomic-embed-text", prompt=query)["embedding"]
    q_emb = np.array(q_emb)
    sims = [np.dot(q_emb, emb) for emb in embeddings]
    for i, sim in enumerate(sims):
        print(f"Similarity with doc {i+1} ({filenames[i]}): {sim:.4f}")
    top_k_idx = np.argsort(sims)[-k:][::-1]

    results = []
    for idx in top_k_idx:
        text = texts[idx]
        filename = filenames[idx]
        snippet = ""
        for word in query.split():
            pos = text.lower().find(word.lower())
            if pos != -1:
                start = max(0, pos - window)
                end = min(len(text), pos + window)
                snippet = text[start:end].replace("\n", " ")
                # Simple highlight, case-insensitive
                snippet = snippet.replace(word, f"**{word}**")
                break
        if not snippet:
            snippet = text[: window * 2].replace("\n", " ")
        results.append((filename, snippet))
    return results


wiki_dir = os.path.expanduser("~/wiki")
texts = []
filenames = []
for filename in os.listdir(wiki_dir):
    path = os.path.join(wiki_dir, filename)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            texts.append(f.read())
        filenames.append(filename)

print(f"Loaded {len(texts)} documents from {wiki_dir}")

embeddings = embed_text(texts)

# Example search
query = "Charactererstellung"
results = get_top_k(query, embeddings, texts, filenames)

print("\nTop matches:")
for fn, snippet in results:
    print(f"File: {fn}\nSnippet: {snippet}\n")
