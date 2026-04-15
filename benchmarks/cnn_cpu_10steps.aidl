py import numpy as np

f conv2d_valid(x, w, b)
  = n x.shape[0]
  = in_c x.shape[1]
  = h x.shape[2]
  = width x.shape[3]
  = out_c w.shape[0]
  = kh w.shape[2]
  = kw w.shape[3]
  = out_h h - kh + 1
  = out_w width - kw + 1
  py out = np.zeros((n, out_c, out_h, out_w), dtype=np.float32)
  for batch in range(n)
    for oc in range(out_c)
      for i in range(out_h)
        for j in range(out_w)
          py patch = x[batch, :, i : i + kh, j : j + kw]
          py out[batch, oc, i, j] = np.sum(patch * w[oc]) + b[oc]
  r out

f conv2d_backward(x, w, grad_out)
  = n x.shape[0]
  = in_c x.shape[1]
  = h x.shape[2]
  = width x.shape[3]
  = out_c w.shape[0]
  = kh w.shape[2]
  = kw w.shape[3]
  = out_h grad_out.shape[2]
  = out_w grad_out.shape[3]
  py grad_x = np.zeros_like(x)
  py grad_w = np.zeros_like(w)
  py grad_b = np.zeros((out_c,), dtype=np.float32)
  for batch in range(n)
    for oc in range(out_c)
      for i in range(out_h)
        for j in range(out_w)
          = grad grad_out[batch, oc, i, j]
          py patch = x[batch, :, i : i + kh, j : j + kw]
          py grad_w[oc] += grad * patch
          py grad_x[batch, :, i : i + kh, j : j + kw] += grad * w[oc]
          py grad_b[oc] += grad
  r (grad_x, grad_w, grad_b)

f softmax_cross_entropy(logits, targets)
  = shifted logits - logits.max(axis=1, keepdims=True)
  = exp np.exp(shifted)
  = probs exp / exp.sum(axis=1, keepdims=True)
  = loss -np.log(probs[np.arange(targets.shape[0]), targets]).mean()
  py grad = probs.copy()
  py grad[np.arange(targets.shape[0]), targets] -= 1.0
  py grad /= targets.shape[0]
  r (loss, grad)

py rng = np.random.default_rng(0)
py x = rng.normal(0.0, 1.0, size=(8, 1, 6, 6)).astype(np.float32)
py y = rng.integers(0, 2, size=(8,), endpoint=False)

py conv_w = (rng.normal(0.0, 0.2, size=(2, 1, 3, 3))).astype(np.float32)
py conv_b = np.zeros((2,), dtype=np.float32)
py fc_w = (rng.normal(0.0, 0.2, size=(2 * 4 * 4, 2))).astype(np.float32)
py fc_b = np.zeros((2,), dtype=np.float32)
= lr 0.05

for step in range(10)
  = conv conv2d_valid(x, conv_w, conv_b)
  = relu np.maximum(conv, 0.0)
  = flat relu.reshape(relu.shape[0], -1)
  = logits flat @ fc_w + fc_b
  = loss_grad softmax_cross_entropy(logits, y)
  = loss loss_grad[0]
  = grad_logits loss_grad[1]

  = grad_fc_w flat.T @ grad_logits
  = grad_fc_b grad_logits.sum(axis=0)
  = grad_flat grad_logits @ fc_w.T
  = grad_relu grad_flat.reshape(relu.shape)
  = grad_conv grad_relu * (conv > 0.0)
  = conv_back conv2d_backward(x, conv_w, grad_conv)
  = grad_conv_w conv_back[1]
  = grad_conv_b conv_back[2]

  py fc_w -= lr * grad_fc_w
  py fc_b -= lr * grad_fc_b
  py conv_w -= lr * grad_conv_w
  py conv_b -= lr * grad_conv_b

  py print(f"step={step} loss={loss:.6f}")
