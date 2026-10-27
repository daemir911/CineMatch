"""
End-to-End Training Pipeline for Universal Scalable Hybrid Movie Recommender System.
Optimized for the Expanded 13,000+ Movie Catalog:
1. Content-based feature extraction with PorterStemmer + CountVectorizer (6,000 features).
2. L2-normalized sparse representation for sub-5ms cosine similarity dot-product recommendations.
3. Collaborative filtering latent item embeddings via Surprise SVD (with TruncatedSVD fallback).
4. Hybrid score blending: score = alpha * content + (1 - alpha) * collab, with cold-start safety.
5. Precision@10 & Recall@10 evaluation against holdout user rating histories.
6. Artifact exports: movies.pkl, vectors.pkl, vectorizer.pkl, collab_factors.pkl,
   content_sim.pkl, collab_sim.pkl.
"""
import os
import ast
import time
import logging
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from nltk.stem.porter import PorterStemmer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

import config
import network_utils

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TrainPipeline")

stemmer = PorterStemmer()

def parse_list_items(val):
    if pd.isna(val) or val is None:
        return []
    if isinstance(val, list):
        return [str(x) for x in val if x]
    if isinstance(val, str):
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                items = ast.literal_eval(val)
                if isinstance(items, list):
                    return [str(x) for x in items if x]
            except Exception:
                pass
        if "|" in val:
            return [x.strip() for x in val.split("|") if x.strip()]
        if "," in val:
            return [x.strip() for x in val.split(",") if x.strip()]
        return [val] if val else []
    return []

def clean_tokens(tokens):
    """Lowercases and strips spaces to preserve entity names intact."""
    return [str(t).replace(" ", "").lower() for t in tokens if t]

def stem_words(tokens):
    """Applies PorterStemmer to a list of tokens."""
    return [stemmer.stem(w) for w in tokens]

def load_data():
    logger.info("Loading movie catalog and rating datasets...")
    
    # Check if catalog CSV exists
    if config.CATALOG_CSV.exists():
        logger.info("Loading expanded catalog from %s ...", config.CATALOG_CSV.name)
        df = pd.read_csv(config.CATALOG_CSV)
    elif config.MOVIES_PKL.exists():
        logger.info("Loading catalog from %s ...", config.MOVIES_PKL.name)
        df = joblib.load(config.MOVIES_PKL)
    else:
        raise FileNotFoundError(f"Neither {config.CATALOG_CSV} nor {config.MOVIES_PKL} exists. Run scripts/build_catalog.py first.")

    # Harmonize id and tmdb_id
    if 'id' not in df.columns and 'tmdb_id' in df.columns:
        df['id'] = df['tmdb_id']
    if 'vote_average' not in df.columns and 'rating' in df.columns:
        df['vote_average'] = df['rating']

    # Load ratings and links
    if not config.RATINGS_CSV.exists() or not config.LINKS_CSV.exists():
        raise FileNotFoundError(f"Missing ratings or links datasets in {config.DATA_DIR}")

    ratings_df = pd.read_csv(config.RATINGS_CSV)
    links_df = pd.read_csv(config.LINKS_CSV).dropna(subset=['tmdbId'])
    links_df['tmdbId'] = links_df['tmdbId'].astype(int)

    logger.info("Loaded catalog with %d movies. MovieLens ratings: %d across %d users.",
                len(df), len(ratings_df), ratings_df['userId'].nunique())
    return df, links_df, ratings_df

def build_content_model(df):
    logger.info("Building Content-Based Feature Model for %d movies...", len(df))

    # Parse and clean metadata
    logger.info("Extracting and tokenizing plot overview, genres, cast, keywords, and director...")
    genres_series = df['genres'].apply(parse_list_items)
    keywords_series = df['keywords'].apply(parse_list_items)
    cast_series = df['cast'].apply(parse_list_items)
    
    # Store parsed versions in df
    df['parsed_genres'] = genres_series
    df['parsed_cast'] = cast_series
    df['parsed_director'] = df['director'].fillna('Unknown').astype(str)
    df['parsed_keywords'] = keywords_series

    # Token lists for tag construction
    clean_genres = genres_series.apply(clean_tokens)
    clean_keywords = keywords_series.apply(clean_tokens)
    clean_cast = cast_series.apply(clean_tokens)
    clean_director = df['parsed_director'].apply(lambda d: [clean_tokens([d])[0]] if d and d != "Unknown" else [])
    clean_overview = df['overview'].fillna('').apply(lambda text: [w.lower() for w in str(text).split() if len(w) > 2])

    # Combine into tags
    df['tags'] = clean_overview + clean_genres + clean_keywords + clean_cast + clean_director
    
    logger.info("Stemming tags using NLTK PorterStemmer...")
    tags_string = df['tags'].apply(lambda tokens: ' '.join(stem_words(tokens)))
    df['tags_string'] = tags_string

    # Vectorize
    logger.info("Vectorizing tags with CountVectorizer (max_features=%d)...", config.MAX_FEATURES)
    cv = CountVectorizer(max_features=config.MAX_FEATURES, stop_words='english', dtype=np.float32)
    raw_vectors = cv.fit_transform(tags_string)

    # L2-normalize vectors for ultra-fast cosine similarity dot products
    logger.info("L2-normalizing feature vectors...")
    norm_vectors = normalize(raw_vectors, norm='l2', copy=False)
    logger.info("Feature vector matrix ready: shape %s, sparse format CSR.", norm_vectors.shape)

    return df, cv, norm_vectors

def build_collaborative_model(df, links_df, ratings_df, norm_vectors):
    logger.info("Building Collaborative Filtering Model with latent SVD factor embeddings...")

    # Filter ratings to catalog
    merged_ratings = ratings_df.merge(links_df[['movieId', 'tmdbId']], on='movieId')
    catalog_tmdb_ids = set(df['id'])
    matched_ratings = merged_ratings[merged_ratings['tmdbId'].isin(catalog_tmdb_ids)].copy()
    logger.info("Matched %d ratings for collaborative modeling across %d movies.",
                len(matched_ratings), matched_ratings['tmdbId'].nunique())

    use_surprise = True
    try:
        from surprise import Dataset, Reader, SVD
        from surprise.model_selection import train_test_split
        from surprise import accuracy
    except ImportError:
        use_surprise = False
        logger.warning("Surprise is not installed. Falling back to scikit-learn TruncatedSVD.")

    factors_dict = {}

    if use_surprise:
        logger.info("Training Surprise SVD model (n_factors=%d)...", config.SVD_FACTORS)
        reader = Reader(rating_scale=(0.5, 5.0))
        data = Dataset.load_from_df(matched_ratings[['userId', 'tmdbId', 'rating']], reader)

        # Train-test split for evaluation
        trainset_split, testset_split = train_test_split(data, test_size=0.2, random_state=config.RANDOM_STATE)
        eval_svd = SVD(n_factors=config.SVD_FACTORS, random_state=config.RANDOM_STATE)
        eval_svd.fit(trainset_split)
        preds = eval_svd.test(testset_split)
        rmse = accuracy.rmse(preds, verbose=False)
        mae = accuracy.mae(preds, verbose=False)
        logger.info(">>> Surprise SVD Evaluation: RMSE = %.4f | MAE = %.4f", rmse, mae)

        # Train full SVD on all ratings
        full_trainset = data.build_full_trainset()
        full_svd = SVD(n_factors=config.SVD_FACTORS, random_state=config.RANDOM_STATE)
        full_svd.fit(full_trainset)

        for tid in df['id']:
            try:
                inner_id = full_trainset.to_inner_iid(tid)
                factors_dict[tid] = full_svd.qi[inner_id]
            except ValueError:
                factors_dict[tid] = None
    else:
        # Fallback using TruncatedSVD on User-Item Pivot
        logger.info("Executing TruncatedSVD fallback on user-item matrix...")
        from sklearn.decomposition import TruncatedSVD
        pivot = matched_ratings.pivot_table(index='tmdbId', columns='userId', values='rating').fillna(0)
        tsvd = TruncatedSVD(n_components=config.SVD_FACTORS, random_state=config.RANDOM_STATE)
        factors_arr = tsvd.fit_transform(pivot)
        for idx, tid in enumerate(pivot.index):
            factors_dict[tid] = factors_arr[idx]

    # Build aligned factors array
    factors_list = []
    has_collab_list = []

    for tid in df['id']:
        vec = factors_dict.get(tid)
        if vec is not None:
            factors_list.append(vec)
            has_collab_list.append(True)
        else:
            factors_list.append(np.zeros(config.SVD_FACTORS, dtype=np.float32))
            has_collab_list.append(False)

    item_factors = np.array(factors_list, dtype=np.float32)

    # Normalize rated factors
    has_norm = np.array(has_collab_list, dtype=bool)
    norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
    valid_rated = has_norm & (norms.flatten() > 0)
    item_factors[valid_rated] = item_factors[valid_rated] / norms[valid_rated]

    # Ridge projection for unrated movies to project them into collaborative space
    unrated_idx = np.where(~valid_rated)[0]
    if len(unrated_idx) > 0 and valid_rated.sum() > 0:
        logger.info("Projecting collaborative factors for %d unrated movies via content embeddings...", len(unrated_idx))
        from sklearn.linear_model import Ridge
        ridge = Ridge(alpha=10.0)
        ridge.fit(norm_vectors[valid_rated], item_factors[valid_rated])
        item_factors[unrated_idx] = ridge.predict(norm_vectors[unrated_idx])

    # Re-normalize all factor vectors to unit length
    final_norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
    final_norms[final_norms == 0.0] = 1.0
    norm_item_factors = item_factors / final_norms

    # All movies now have collaborative embeddings
    df['has_collab'] = True
    logger.info("Collaborative latent factors successfully generated for 100%% of catalog (%d movies).", len(df))

    return df, norm_item_factors, matched_ratings

def compute_similarity_matrices(df, norm_vectors, norm_item_factors):
    """
    Computes precomputed similarity matrices in float16 for fast in-RAM access,
    guaranteeing strict backward compatibility with any precomputed lookup.
    """
    N = len(df)
    logger.info("Computing precomputed similarity matrices for %d movies (float16)...", N)

    # Content similarity (chunked to preserve memory)
    content_sim = np.zeros((N, N), dtype=np.float16)
    chunk_size = 2000
    for i in range(0, N, chunk_size):
        end = min(i + chunk_size, N)
        chunk_sim = norm_vectors[i:end].dot(norm_vectors.T).toarray()
        np.clip(chunk_sim, 0.0, 1.0, out=chunk_sim)
        content_sim[i:end] = chunk_sim.astype(np.float16)

    # Collaborative similarity (chunked dot product)
    collab_sim = np.zeros((N, N), dtype=np.float16)
    for i in range(0, N, chunk_size):
        end = min(i + chunk_size, N)
        chunk_cl = norm_item_factors[i:end].dot(norm_item_factors.T)
        collab_sim[i:end] = chunk_cl.astype(np.float16)

    logger.info("Similarity matrices computed successfully: content_sim %s, collab_sim %s",
                content_sim.shape, collab_sim.shape)
    return content_sim, collab_sim

def evaluate_recommender(df, norm_vectors, norm_item_factors, matched_ratings, k=10):
    logger.info("Running Recommender Evaluation (Precision@%d & Recall@%d)...", k, k)
    has_collab_mask = df['has_collab'].values
    tmdb_to_idx = {tid: i for i, tid in enumerate(df['id'])}

    high_ratings = matched_ratings[matched_ratings['rating'] >= 4.0]
    user_counts = high_ratings.groupby('userId').size()
    sample_users = user_counts[user_counts >= 15].index.tolist()[:100]

    prec_content, rec_content = [], []
    prec_collab, rec_collab = [], []
    prec_hybrid, rec_hybrid = [], []

    for user_id in sample_users:
        user_movies = high_ratings[high_ratings['userId'] == user_id]['tmdbId'].tolist()
        user_movie_indices = [tmdb_to_idx[tid] for tid in user_movies if tid in tmdb_to_idx]
        if len(user_movie_indices) < 8:
            continue

        n_seed = max(1, int(len(user_movie_indices) * 0.7))
        seed_indices = user_movie_indices[:n_seed]
        holdout_set = set(user_movie_indices[n_seed:])
        if not holdout_set:
            continue

        for mode, prec_list, rec_list in [
            ('content', prec_content, rec_content),
            ('collab', prec_collab, rec_collab),
            ('hybrid', prec_hybrid, rec_hybrid)
        ]:
            total_scores = np.zeros(len(df), dtype=np.float32)
            for s_idx in seed_indices:
                c_s = norm_vectors[s_idx].dot(norm_vectors.T).toarray()[0]
                cl_s = norm_item_factors[s_idx].dot(norm_item_factors.T)
                if mode == 'content':
                    total_scores += c_s
                elif mode == 'collab':
                    total_scores += cl_s
                else:
                    if not has_collab_mask[s_idx]:
                        total_scores += c_s
                    else:
                        h_s = (config.DEFAULT_ALPHA * c_s) + ((1.0 - config.DEFAULT_ALPHA) * cl_s)
                        h_s[~has_collab_mask] = c_s[~has_collab_mask]
                        total_scores += h_s

            total_scores[seed_indices] = -1.0
            top_recs = np.argsort(total_scores)[::-1][:k]
            hits = len(set(top_recs).intersection(holdout_set))
            prec_list.append(hits / k)
            rec_list.append(hits / len(holdout_set))

    results_table = pd.DataFrame({
        "Model": ["Content-Only (alpha=1.0)", "Collaborative-Only (alpha=0.0)", f"Hybrid (alpha={config.DEFAULT_ALPHA})"],
        f"Precision@{k}": [np.mean(prec_content), np.mean(prec_collab), np.mean(prec_hybrid)],
        f"Recall@{k}": [np.mean(rec_content), np.mean(rec_collab), np.mean(rec_hybrid)]
    })

    print("\n" + "=" * 65)
    print("           RECOMMENDER EVALUATION COMPARISON TABLE           ")
    print("=" * 65)
    print(results_table.to_string(index=False, formatters={
        f"Precision@{k}": "{:.4f}".format,
        f"Recall@{k}": "{:.4f}".format
    }))
    print("=" * 65 + "\n")

    # Sanity checks on prominent classic and modern movies
    print("=" * 65)
    print("                  MANUAL SANITY CHECKS                       ")
    print("=" * 65)
    test_titles = ["The Dark Knight", "Inception", "Interstellar", "Avatar", "Toy Story", "Oppenheimer"]
    for title in test_titles:
        matches = df[df['title'].str.lower() == title.lower()]
        if matches.empty:
            continue
        m_idx = matches.index[0]
        actual_title = df.loc[m_idx, 'title']
        genres = df.loc[m_idx, 'parsed_genres']
        director = df.loc[m_idx, 'parsed_director']
        year = df.loc[m_idx, 'year']

        c_s = norm_vectors[m_idx].dot(norm_vectors.T).toarray()[0]
        cl_s = norm_item_factors[m_idx].dot(norm_item_factors.T)
        h_s = (config.DEFAULT_ALPHA * c_s) + ((1.0 - config.DEFAULT_ALPHA) * cl_s)
        h_s[m_idx] = -1.0
        top_5 = np.argsort(h_s)[::-1][:5]
        recs_str = ", ".join([f"{df.loc[i, 'title']} ({df.loc[i, 'year']})" for i in top_5])
        print(f"\nTarget: {actual_title} ({year}) | Dir: {director} | Genres: {', '.join(genres[:2])}")
        print(f"  [Hybrid Recs] -> {recs_str}")
    print("=" * 65 + "\n")

def save_artifacts(df, cv, norm_vectors, norm_item_factors, content_sim, collab_sim):
    logger.info("Saving model artifacts to %s ...", config.MODEL_DIR)
    os.makedirs(config.MODEL_DIR, exist_ok=True)

    # Standard clean metadata schema for backend
    cols_to_keep = [
        'id', 'tmdb_id', 'title', 'year', 'genres', 'cast',
        'director', 'keywords', 'overview', 'rating', 'vote_average',
        'vote_count', 'popularity', 'poster_path', 'poster_url',
        'backdrop_url', 'tagline', 'language', 'has_collab'
    ]
    # Ensure all columns exist
    for col in cols_to_keep:
        if col not in df.columns:
            if col == 'genres': df[col] = df['parsed_genres']
            elif col == 'cast': df[col] = df['parsed_cast']
            elif col == 'director': df[col] = df['parsed_director']
            elif col == 'keywords': df[col] = df['parsed_keywords']
            else: df[col] = None

    movies_export = df[cols_to_keep].copy()

    # Save artifacts
    logger.info("Saving %s ...", config.MOVIES_PKL.name)
    joblib.dump(movies_export, config.MOVIES_PKL)

    logger.info("Saving %s ...", config.VECTORIZER_PKL.name)
    joblib.dump(cv, config.VECTORIZER_PKL)

    logger.info("Saving %s ...", config.VECTORS_PKL.name)
    joblib.dump(norm_vectors, config.VECTORS_PKL)

    logger.info("Saving %s ...", config.COLLAB_FACTORS_PKL.name)
    joblib.dump(norm_item_factors, config.COLLAB_FACTORS_PKL)

    logger.info("Saving %s ...", config.CONTENT_SIM_PKL.name)
    joblib.dump(content_sim, config.CONTENT_SIM_PKL)

    logger.info("Saving %s ...", config.COLLAB_SIM_PKL.name)
    joblib.dump(collab_sim, config.COLLAB_SIM_PKL)

    logger.info("All artifacts successfully exported.")

def run_pipeline():
    start_time = time.time()
    logger.info("Starting Universal Hybrid Recommender Training Pipeline...")

    df, links_df, ratings_df = load_data()
    df, cv, norm_vectors = build_content_model(df)
    df, norm_item_factors, matched_ratings = build_collaborative_model(df, links_df, ratings_df, norm_vectors)
    content_sim, collab_sim = compute_similarity_matrices(df, norm_vectors, norm_item_factors)
    evaluate_recommender(df, norm_vectors, norm_item_factors, matched_ratings, k=config.DEFAULT_RECOMMEND_COUNT)
    save_artifacts(df, cv, norm_vectors, norm_item_factors, content_sim, collab_sim)

    elapsed = time.time() - start_time
    logger.info("Pipeline completed successfully in %.2f seconds.", elapsed)

if __name__ == "__main__":
    run_pipeline()
