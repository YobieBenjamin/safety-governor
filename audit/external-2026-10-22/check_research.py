"""Check the auditor's research numbers from the committed YB-0051 scores. Run from the YB-0051 folder."""
import sys, numpy as np
sys.path.insert(0, "tests"); sys.path.insert(0, "src")
from candidates import fit_c2, c2, pct, neg
from sklearn.linear_model import LogisticRegression
R = dict(np.load("data/explore_scores.npz", allow_pickle=True)); Z = dict(np.load("data/test_scores.npz", allow_pickle=True))
y = np.asarray(Z["y"]); cat = np.asarray(Z["cat"]); c0 = y == 0

def thr_at(s, cap):                 # the published rule: threshold set on the test set's correct answers
    v = np.sort(s[c0])[::-1]; k = int(np.floor((cap + 1e-12) * c0.sum())); return v[k]

m = fit_c2(R); s = c2(m, Z, R, Z["d4"]); t = thr_at(s, 0.01); a = s > t
print(f"C2 at 1% (threshold from test labels, as published): caught {int(a[y==1].sum())} of {int(y.sum())}, false alarms {int(a[c0].sum())} of {int(c0.sum())} = {a[c0].mean():.3%}")
print("false alarms by task family:")
for c in sorted(set(cat.tolist())):
    mk = (cat == c) & c0
    print(f"  {c:9s} {int(a[mk].sum()):3d} of {int(mk.sum()):4d} = {a[mk].mean():6.2%}   errors caught {int(a[(cat==c)&(y==1)].sum())} of {int(((cat==c)&(y==1)).sum())}")

# the cheaper baseline: self-consistency plus the trained text monitor, same regularisation, fitted on the reference
def feats_sct(D, dkey): return np.c_[np.asarray(D[dkey], float), pct(D["text"], R["text"])]
b = LogisticRegression(C=1.0, max_iter=5000).fit(feats_sct(R, "d"), np.asarray(R["y"])).predict_proba(feats_sct(Z, "d4"))[:, 1]
fa = int(a[c0].sum())
order = np.sort(b[c0])[::-1]; tb = order[fa]          # same number of false alarms as C2
ab = b > tb
print(f"SC + text at C2's {fa} false alarms: caught {int(ab[y==1].sum())} (C2: {int(a[y==1].sum())}); false alarms {int(ab[c0].sum())}")

# a threshold frozen before the test: set on the reference's correct answers at 1%
sr = c2(m, R, R, R["d"]); yr = np.asarray(R["y"]); v = np.sort(sr[yr==0])[::-1]; tf = v[int(np.floor(0.01 * (yr==0).sum()))]
af = s > tf
print(f"C2 with the threshold frozen on the reference: caught {int(af[y==1].sum())}, false alarms {int(af[c0].sum())} = {af[c0].mean():.3%}")
mk = (cat == "modpow") & c0 if "modpow" in set(cat.tolist()) else None
if mk is not None: print(f"  of which modpow: {int(af[mk].sum())} of {int(mk.sum())} = {af[mk].mean():.2%}")
