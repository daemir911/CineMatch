import joblib
import numpy as np

df = joblib.load('model/movies.pkl')
csim = joblib.load('model/content_sim.pkl')
clsim = joblib.load('model/collab_sim.pkl')
factors = joblib.load('model/collab_factors.pkl')

target_idx = df[df['title'].str.contains('Avengers: Endgame', case=False, na=False)].index[0]
print('Target:', df.iloc[target_idx]['title'], target_idx)

# Method 1: direct clsim
cl_raw1 = clsim[target_idx].astype(np.float32).copy()
cl_raw1[target_idx] = -1.0

# Method 2: clsim with confidence
votes = df['vote_count'].values.astype(np.float32)
confidence = np.log1p(votes) / (np.log1p(votes) + 1.5)
cl_raw2 = (factors.dot(factors[target_idx]) * confidence).astype(np.float32)
cl_raw2[target_idx] = -1.0

top1 = np.argsort(cl_raw1)[::-1][:10]
print('\nTop 10 Collab without confidence:')
for idx in top1:
    print(f"- {df.iloc[idx]['title']} ({df.iloc[idx]['year']}) | votes: {df.iloc[idx]['vote_count']} | raw: {cl_raw1[idx]:.3f}")

top2 = np.argsort(cl_raw2)[::-1][:10]
print('\nTop 10 Collab with confidence:')
for idx in top2:
    print(f"- {df.iloc[idx]['title']} ({df.iloc[idx]['year']}) | votes: {df.iloc[idx]['vote_count']} | raw: {cl_raw2[idx]:.3f}")

# Method 3: Content sim
c_raw = csim[target_idx].astype(np.float32).copy()
c_raw[target_idx] = -1.0
top_c = np.argsort(c_raw)[::-1][:10]
print('\nTop 10 Content:')
for idx in top_c:
    print(f"- {df.iloc[idx]['title']} ({df.iloc[idx]['year']}) | raw: {c_raw[idx]:.3f}")

