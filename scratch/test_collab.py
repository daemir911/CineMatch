import pandas as pd
import joblib
import numpy as np
from sklearn.decomposition import TruncatedSVD
from scipy import sparse
from sklearn.linear_model import Ridge

df = joblib.load('model/movies.pkl')
vectors = joblib.load('model/vectors.pkl')
links = pd.read_csv('data/links.csv').dropna(subset=['tmdbId'])
links['tmdbId'] = links['tmdbId'].astype(int)
ratings = pd.read_csv('data/ratings.csv')

merged = ratings.merge(links, on='movieId')
tmdb_to_row = {tid: i for i, tid in enumerate(df['id'])}

valid_ratings = merged[merged['tmdbId'].isin(tmdb_to_row)].copy()
valid_ratings['row_idx'] = valid_ratings['tmdbId'].map(tmdb_to_row)
valid_ratings['user_idx'] = valid_ratings['userId'].astype('category').cat.codes

n_movies = len(df)
n_users = valid_ratings['user_idx'].nunique()

# Mean-center ratings per user
user_means = valid_ratings.groupby('user_idx')['rating'].mean()
valid_ratings['centered_rating'] = valid_ratings['rating'] - valid_ratings['user_idx'].map(user_means)

row_idx = valid_ratings['row_idx'].values
col_idx = valid_ratings['user_idx'].values
data = valid_ratings['centered_rating'].values

R_sparse = sparse.csr_matrix((data, (row_idx, col_idx)), shape=(n_movies, n_users), dtype=np.float32)

svd = TruncatedSVD(n_components=30, random_state=42)
item_factors = svd.fit_transform(R_sparse)

# Rated mask
rated_mask = np.zeros(n_movies, dtype=bool)
rated_mask[valid_ratings['row_idx'].unique()] = True

norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
has_norm = (norms > 0).flatten() & rated_mask
item_factors[has_norm] = item_factors[has_norm] / norms[has_norm]

# Ridge projection for unrated movies
ridge = Ridge(alpha=10.0)
ridge.fit(vectors[has_norm], item_factors[has_norm])
unrated = np.where(~has_norm)[0]
item_factors[unrated] = ridge.predict(vectors[unrated])
norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
norms[norms == 0.0] = 1.0
item_factors = item_factors / norms

# Weight by popularity / rating count so zero-vote coincidences don't dominate
votes = df['vote_count'].values.astype(np.float32)
confidence = np.log1p(votes) / (np.log1p(votes) + 1.5)

# Test for Avengers: Endgame (299534)
endgame_idx = tmdb_to_row[299534]
c_sim = joblib.load('model/content_sim.pkl')

c_raw = c_sim[endgame_idx].astype(np.float32)
cl_raw = item_factors.dot(item_factors[endgame_idx]) * confidence

c_raw[endgame_idx] = -1.0
cl_raw[endgame_idx] = -1.0

# Rank-based / Min-Max normalization to [0, 1] range
c_val = c_raw[c_raw >= 0]
cl_val = cl_raw[cl_raw >= 0]

c_norm = np.clip((c_raw - c_val.min()) / (c_val.max() - c_val.min() + 1e-8), 0.0, 1.0)
cl_norm = np.clip((cl_raw - cl_val.min()) / (cl_val.max() - cl_val.min() + 1e-8), 0.0, 1.0)

for alpha in [1.0, 0.6, 0.0]:
    blend = alpha * c_norm + (1.0 - alpha) * cl_norm
    blend[endgame_idx] = -1.0
    top10 = np.argsort(blend)[::-1][:10]
    print(f"\n=================== AVENGERS: ENDGAME (ALPHA = {alpha}) ===================")
    for rank, idx in enumerate(top10, 1):
        m = df.iloc[idx]
        print(f"{rank:2d}. {m['title']} ({m['year']}) | Match: {blend[idx]*100:.1f}% | Plot & Cast: {c_norm[idx]*100:.1f}% | Viewer Ratings: {cl_norm[idx]*100:.1f}%")
