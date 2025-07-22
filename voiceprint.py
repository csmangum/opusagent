import os

import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
from mpl_toolkits.mplot3d import Axes3D
from openai import OpenAI
from resemblyzer import VoiceEncoder, preprocess_wav
from scipy.spatial.distance import cosine
import umap

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# List of available OpenAI TTS voices (as of 2025; confirmed to be these based on documentation)
voices = [
    "alloy",
    "ash",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]

# Sample text to synthesize
text = "Hello, this is a test sentence for voice fingerprinting. Let's see how different voices sound."

# Generate audio files for each voice
audio_files = []
for voice in voices:
    response = client.audio.speech.create(
        model="tts-1",  # You can change to "tts-1-hd" for higher quality
        voice=voice,
        input=text,
        response_format="mp3",  # MP3 format for compatibility
    )
    file_path = f"{voice}.mp3"
    with open(file_path, "wb") as f:
        f.write(response.content)
    audio_files.append(file_path)
    print(f"Generated audio file: {file_path}")

# Initialize Resemblyzer VoiceEncoder
encoder = VoiceEncoder()
print("Initialized VoiceEncoder")

# Extract voice embeddings using Resemblyzer
embeddings = {}
embedding_array = []
for file in audio_files:
    # Load and preprocess audio for Resemblyzer
    wav = preprocess_wav(file)
    embedding = encoder.embed_utterance(wav)
    embeddings[file.split(".")[0]] = embedding  # Key by voice name
    embedding_array.append(embedding)
    print(
        f"Extracted Resemblyzer embedding for {file} (shape: {np.array(embedding).shape})"
    )

embedding_array = np.array(embedding_array)  # Shape: (num_voices, 256)


# Function to perform PCA with NumPy
def pca(data, n_components=3):
    mean = np.mean(data, axis=0)
    centered = data - mean
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)  # Use eigh for symmetric matrices
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]
    projected = np.dot(centered, eigenvectors[:, :n_components])
    return np.real(projected)  # Ensure real output


# Reduce embeddings to 3D space using PCA
reduced_embeddings_pca = pca(embedding_array, 3)
print("\n3D Reduced Embeddings (PCA):")
for voice, coords in zip(voices, reduced_embeddings_pca):
    print(f"{voice}: {coords}")

# Visualize PCA in 3D space
fig = plt.figure(figsize=(12, 5))
ax1 = fig.add_subplot(121, projection="3d")
scatter1 = ax1.scatter(
    reduced_embeddings_pca[:, 0], reduced_embeddings_pca[:, 1], reduced_embeddings_pca[:, 2]
)

# Label each point with the voice name
for i, voice in enumerate(voices):
    ax1.text(reduced_embeddings_pca[i, 0], reduced_embeddings_pca[i, 1], reduced_embeddings_pca[i, 2], voice, fontsize=10)  # type: ignore

ax1.set_title("PCA 3D Visualization")
ax1.set_xlabel("PC1")
ax1.set_ylabel("PC2")
ax1.set_zlabel("PC3")  # type: ignore

# UMAP dimensionality reduction
print("\nPerforming UMAP dimensionality reduction...")
reducer = umap.UMAP(n_components=3, random_state=42, n_neighbors=3, min_dist=0.1)
reduced_embeddings_umap = reducer.fit_transform(embedding_array)

print("\n3D Reduced Embeddings (UMAP):")
for voice, coords in zip(voices, reduced_embeddings_umap):
    print(f"{voice}: {coords}")

# Visualize UMAP in 3D space
ax2 = fig.add_subplot(122, projection="3d")
scatter2 = ax2.scatter(
    reduced_embeddings_umap[:, 0], reduced_embeddings_umap[:, 1], reduced_embeddings_umap[:, 2]
)

# Label each point with the voice name
for i, voice in enumerate(voices):
    ax2.text(reduced_embeddings_umap[i, 0], reduced_embeddings_umap[i, 1], reduced_embeddings_umap[i, 2], voice, fontsize=10)  # type: ignore

ax2.set_title("UMAP 3D Visualization")
ax2.set_xlabel("UMAP1")
ax2.set_ylabel("UMAP2")
ax2.set_zlabel("UMAP3")  # type: ignore

plt.tight_layout()
plt.show()

# Also create 2D UMAP visualization for better clustering view
print("\nCreating 2D UMAP visualization...")
reducer_2d = umap.UMAP(n_components=2, random_state=42, n_neighbors=3, min_dist=0.1)
reduced_embeddings_umap_2d = reducer_2d.fit_transform(embedding_array)

fig2, ax3 = plt.subplots(figsize=(10, 8))
scatter3 = ax3.scatter(reduced_embeddings_umap_2d[:, 0], reduced_embeddings_umap_2d[:, 1])

# Label each point with the voice name
for i, voice in enumerate(voices):
    ax3.text(reduced_embeddings_umap_2d[i, 0], reduced_embeddings_umap_2d[i, 1], voice, fontsize=12)

ax3.set_title("2D UMAP Visualization of Voice Embeddings")
ax3.set_xlabel("UMAP1")
ax3.set_ylabel("UMAP2")
plt.show()

# Compare original embeddings using cosine similarity (matching the implementation)
print("\nVoice Embedding Similarities (Cosine Distance):")
similarity_threshold = 0.75  # As used in the implementation
for i in range(len(voices)):
    for j in range(i + 1, len(voices)):
        # Calculate cosine distance (1 - cosine similarity)
        distance = cosine(embedding_array[i], embedding_array[j])
        similarity = 1 - distance  # Convert to similarity score

        print(f"Similarity between {voices[i]} and {voices[j]}: {similarity:.4f}")

        # Check if above threshold (as in the implementation)
        if similarity > similarity_threshold:
            print(f"  -> MATCH: Above threshold ({similarity_threshold})")
        else:
            print(f"  -> NO MATCH: Below threshold ({similarity_threshold})")

# Test voice matching functionality (like in the implementation)
print("\nVoice Matching Tests:")
test_voice = "alloy"
test_embedding = embedding_array[voices.index(test_voice)]

print(f"Testing matching for voice: {test_voice}")
matches = []
for i, voice in enumerate(voices):
    if voice != test_voice:
        distance = cosine(test_embedding, embedding_array[i])
        similarity = 1 - distance
        if similarity > similarity_threshold:
            matches.append((voice, similarity))
        print(f"  vs {voice}: {similarity:.4f}")

if matches:
    matches.sort(key=lambda x: x[1], reverse=True)
    print(f"Matches found: {matches}")
else:
    print("No matches found above threshold")

# Notes:
# - Uses Resemblyzer VoiceEncoder for 256-dimensional voice embeddings
# - Implements cosine distance matching as described in the implementation
# - Uses similarity threshold of 0.75 for voice matching
# - PCA reduces 256D embeddings to 3D for visualization
# - Install required libraries: pip install resemblyzer openai numpy scipy matplotlib
# - This matches the voice fingerprinting implementation approach
