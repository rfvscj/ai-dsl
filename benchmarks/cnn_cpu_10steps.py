import numpy as np


def conv2d_valid(x, w, b):
    n, _, h, width = x.shape
    out_c, _, kh, kw = w.shape
    out_h = h - kh + 1
    out_w = width - kw + 1
    out = np.zeros((n, out_c, out_h, out_w), dtype=np.float32)
    for batch in range(n):
        for oc in range(out_c):
            for i in range(out_h):
                for j in range(out_w):
                    patch = x[batch, :, i : i + kh, j : j + kw]
                    out[batch, oc, i, j] = np.sum(patch * w[oc]) + b[oc]
    return out


def conv2d_backward(x, w, grad_out):
    n, in_c, h, width = x.shape
    out_c, _, kh, kw = w.shape
    _, _, out_h, out_w = grad_out.shape
    grad_x = np.zeros_like(x)
    grad_w = np.zeros_like(w)
    grad_b = np.zeros((out_c,), dtype=np.float32)
    for batch in range(n):
        for oc in range(out_c):
            for i in range(out_h):
                for j in range(out_w):
                    grad = grad_out[batch, oc, i, j]
                    patch = x[batch, :, i : i + kh, j : j + kw]
                    grad_w[oc] += grad * patch
                    grad_x[batch, :, i : i + kh, j : j + kw] += grad * w[oc]
                    grad_b[oc] += grad
    return grad_x, grad_w, grad_b


def softmax_cross_entropy(logits, targets):
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    probs = exp / exp.sum(axis=1, keepdims=True)
    loss = -np.log(probs[np.arange(targets.shape[0]), targets]).mean()
    grad = probs.copy()
    grad[np.arange(targets.shape[0]), targets] -= 1.0
    grad /= targets.shape[0]
    return loss, grad


rng = np.random.default_rng(0)
x = rng.normal(0.0, 1.0, size=(8, 1, 6, 6)).astype(np.float32)
y = rng.integers(0, 2, size=(8,), endpoint=False)

conv_w = (rng.normal(0.0, 0.2, size=(2, 1, 3, 3))).astype(np.float32)
conv_b = np.zeros((2,), dtype=np.float32)
fc_w = (rng.normal(0.0, 0.2, size=(2 * 4 * 4, 2))).astype(np.float32)
fc_b = np.zeros((2,), dtype=np.float32)
lr = 0.05

for step in range(10):
    conv = conv2d_valid(x, conv_w, conv_b)
    relu = np.maximum(conv, 0.0)
    flat = relu.reshape(relu.shape[0], -1)
    logits = flat @ fc_w + fc_b
    loss, grad_logits = softmax_cross_entropy(logits, y)

    grad_fc_w = flat.T @ grad_logits
    grad_fc_b = grad_logits.sum(axis=0)
    grad_flat = grad_logits @ fc_w.T
    grad_relu = grad_flat.reshape(relu.shape)
    grad_conv = grad_relu * (conv > 0.0)
    _, grad_conv_w, grad_conv_b = conv2d_backward(x, conv_w, grad_conv)

    fc_w -= lr * grad_fc_w
    fc_b -= lr * grad_fc_b
    conv_w -= lr * grad_conv_w
    conv_b -= lr * grad_conv_b

    print(f"step={step} loss={loss:.6f}")
