import joblib
import numpy as np
from sklearn.linear_model import Ridge

df = joblib.load('model/movies.pkl')
vectors = joblib.load('model/vectors.pkl')
factors = joblib.load('model/collab_factors.pkl')
mask = df['has_collab'].values

rated_idx = np.where(mask)[0]
unrated_idx = np.where(~mask)[0]

print(f"Rated movies: {len(rated_idx)}, Unrated: {len(unrated_idx)}")

ridge = Ridge(alpha=5.0)
ridge.fit(vectors[rated_idx], factors[rated_idx])

all_factors = factors.copy()
all_factors[unrated_idx] = ridge.predict(vectors[unrated_idx])

# L2-normalize
norms = np.linalg.norm(all_factors, axis=1, keepdims=True)
norms[norms == 0.0] = 1.0
all_factors = all_factors / norms

# Test on Avengers: Endgame
endgame_idx = df[df['title'] == 'Avengers: Endgame'].index[0]
print(f"Endgame found at index {endgame_idx}: {df.iloc[endgame_idx]['title']}")

c_sim = joblib.load('model/content_sim.pkl')
c_scores = c_sim[endgame_idx].astype(np.float32)
cl_scores = all_factors.dot(all_factors[endgame_idx])

# Min-max normalization for candidate scores (excluding self)
c_scores[endgame_idx] = -1.0
cl_scores[endgame_idx] = -1.0

valid_c = c_scores[c_scores >= 0]
valid_cl = cl_scores[cl_scores >= 0]

c_norm = np.clip((c_scores - valid_c.min()) / (valid_c.max() - valid_c.min() + 1e-8), 0.0, 1.0)
cl_norm = np.clip((cl_scores - valid_cl.min()) / (valid_cl.max() - valid_cl.min() + 1e-8), 0.0, 1.0)

for alpha in [1.0, 0.6, 0.0]:
    blend = alpha * c_norm + (1.0 - alpha) * cl_norm
    blend[endgame_idx] = -1.0
    top10 = np.argsort(blend)[::-1][:10]
    print(f"\n=================== TOP 10 FOR ALPHA = {alpha} ===================")
    for rank, idx in enumerate(top10, 1):
        m = df.iloc[idx]
        print(f"{rank:2d}. {m['title']} ({m['year']}) | Blend: {blend[idx]*100:.1f}% | Content: {c_norm[idx]*100:.1f}% | Collab: {cl_norm[idx]*100:.1f}%")
