"""Reproduction of Ponocko & Milanovic (2018), "Forecasting demand flexibility of aggregated residential load using smart
meter data", IEEE Trans. Power Systems 33(5) (reference [10] in docs/references.md). Used only as a comparison.

What the paper specifies (Sec. III-B) and is implemented here:
  - inputs: aggregated active and reactive power (P, Q) per minute, in p.u. of the maximum monthly active load;
  - targets: weighting factors (share of the total active load) of six load categories (Table I), from the sub-metered
    homes;
  - feed-forward network, one hidden layer of 44 neurons (the paper cites n = N / (d ln N) with N = 7 x 1440, d = 2,
    which gives 547, not 44; we use the 44 the paper reports), log-sigmoid hidden
    and tan-sigmoid output transfer functions, Bayesian regularization backpropagation (MATLAB `trainbr`:
    Levenberg-Marquardt with MacKay's evidence updates of the weight-decay and data terms);
  - trained on 7 days, tested on the 8th day using the actual (not forecast) P and Q of the whole aggregation;
  - error: AWFE = |WF_est - WF_real| with WF in p.u. of the average monthly active load of the aggregation (eq. 9).
What is not specified and is our choice (MATLAB defaults): inputs and targets mapped to [-1, 1] (mapminmax), Nguyen-
Widrow-like random initialisation, mu = 0.005, mu up x10 / down x0.1, up to 300 epochs.
"""
import numpy as np


def _mapminmax(a, lo=None, hi=None):
    lo = a.min(axis=0) if lo is None else lo
    hi = a.max(axis=0) if hi is None else hi
    rng = np.where(hi > lo, hi - lo, 1.0)
    return 2 * (a - lo) / rng - 1, lo, hi


def _ftz(a):
    """Flush subnormal numbers to zero (saturated sigmoids produce them; they make BLAS ~100x slower)."""
    a[np.abs(a) < 1e-150] = 0.0
    return a


class PMNet:
    def __init__(self, n_hidden=44, epochs=300, seed=0):
        self.n_hidden, self.epochs, self.seed = n_hidden, epochs, seed

    # --- network ---
    def _unpack(self, w):
        d, h, k = self.d, self.h, self.k
        i = 0
        W1 = w[i:i + d * h].reshape(d, h); i += d * h
        b1 = w[i:i + h]; i += h
        W2 = w[i:i + h * k].reshape(h, k); i += h * k
        b2 = w[i:i + k]
        return W1, b1, W2, b2

    def _forward(self, w, X):
        W1, b1, W2, b2 = self._unpack(w)
        H = 1 / (1 + np.exp(-np.clip(X @ W1 + b1, -30, 30)))
        return H, np.tanh(H @ W2 + b2)

    def _jtj(self, w, X, E):
        """J'J and J'e for e = Y - T, without forming the full Jacobian (one output at a time)."""
        W1, b1, W2, b2 = self._unpack(w)
        H, Y = self._forward(w, X)
        d, h, k = self.d, self.h, self.k
        P = d * h + h + h * k + k
        A = np.zeros((P, P)); g = np.zeros(P)
        Xa = np.hstack([X, np.ones((len(X), 1))])
        dH = H * (1 - H)
        for j in range(k):
            gy = 1 - Y[:, j] ** 2                                   # tansig derivative
            S = (gy[:, None] * W2[:, j][None, :]) * dH              # d y_j / d hidden pre-activation (N x h)
            J1 = (Xa[:, :, None] * S[:, None, :])                   # N x (d+1) x h
            Jw1 = J1[:, :d, :].reshape(len(X), d * h); Jb1 = J1[:, d, :]
            Jw2 = gy[:, None] * H; Jb2 = gy[:, None]
            Jj = _ftz(np.hstack([Jw1, Jb1, Jw2, Jb2]))
            idx = np.r_[np.arange(d * h + h), d * h + h + np.arange(h) * k + j, d * h + h + h * k + j]
            A[np.ix_(idx, idx)] += Jj.T @ Jj
            g[idx] += Jj.T @ E[:, j]
        return _ftz(A), _ftz(g)

    def fit(self, X, T):
        rs = np.random.default_rng(self.seed)
        self.Xlo, self.Xhi = X.min(0), X.max(0)
        self.Tlo, self.Thi = T.min(0), T.max(0)
        Xs = _mapminmax(X, self.Xlo, self.Xhi)[0]; Ts = _mapminmax(T, self.Tlo, self.Thi)[0]
        N = len(X)
        self.d, self.k = X.shape[1], T.shape[1]
        self.h = self.n_hidden or int(round(N / (self.d * np.log(N))))
        P = self.d * self.h + self.h + self.h * self.k + self.k
        W1 = rs.uniform(-1, 1, (self.d, self.h)) * 0.7 * self.h ** (1 / self.d)
        w = np.r_[W1.ravel(), rs.uniform(-1, 1, self.h), rs.uniform(-0.5, 0.5, self.h * self.k), np.zeros(self.k)]
        mu, n_err = 0.005, N * self.k
        E = self._forward(w, Xs)[1] - Ts
        sse, ssw = float((E ** 2).sum()), float((w ** 2).sum())
        alpha, beta = 0.0, 1.0                                       # trainbr initial values
        gamma = P
        for ep in range(self.epochs):
            A, g = self._jtj(w, Xs, E)
            lam, V = np.linalg.eigh(A)                  # one decomposition per epoch; every mu step is then cheap
            lam = np.clip(lam, 0, None)
            lam[lam < 1e-12 * lam.max()] = 0.0
            F = beta * sse + alpha * ssw
            rhs = V.T @ (beta * g + alpha * w)
            while True:
                step = -V @ (rhs / (beta * lam + alpha + mu))
                w2 = w + step
                E2 = self._forward(w2, Xs)[1] - Ts
                sse2, ssw2 = float((E2 ** 2).sum()), float((w2 ** 2).sum())
                if beta * sse2 + alpha * ssw2 < F:
                    mu = max(mu * 0.1, 1e-20)
                    break
                mu *= 10
                if mu > 1e10:
                    break
            if mu > 1e10:
                break
            w, E, sse, ssw = w2, E2, sse2, ssw2
            # MacKay evidence update (as trainbr): effective number of parameters
            gamma = P - alpha * float(np.sum(1.0 / (beta * lam + alpha))) if alpha > 0 else P
            alpha = gamma / (2 * ssw) if ssw > 0 else alpha
            beta = (n_err - gamma) / (2 * sse) if sse > 0 else beta
            if alpha == 0 or ep > 5 and abs(step).max() < 1e-7:
                break
        self.w, self.gamma, self.epochs_run, self.sse = w, gamma, ep + 1, sse
        return self

    def predict(self, X):
        Xs = _mapminmax(X, self.Xlo, self.Xhi)[0]
        Ys = self._forward(self.w, Xs)[1]
        return (Ys + 1) / 2 * (self.Thi - self.Tlo) + self.Tlo


def inputs(P, Q, month_max):
    """P, Q (aggregation, any unit) -> ANN input in p.u. of the maximum monthly active load."""
    return np.column_stack([P / month_max, Q / month_max])


def shares(per_cat, P):
    """Targets: share of each category in the total active load (rows: time, cols: categories)."""
    return per_cat / np.where(P > 0, P, np.nan)[:, None]


def awfe(est_kw, true_kw, mean_month_kw):
    """Eq. (9): absolute error of the category load in p.u. of the average monthly active load of the aggregation."""
    return np.abs(est_kw - true_kw) / mean_month_kw
