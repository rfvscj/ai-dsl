py import torch
py import torch.nn as nn
py import torch.optim as optim

py torch.manual_seed(0)

py model = nn.Sequential(
py     nn.Conv2d(1, 4, kernel_size=3),
py     nn.ReLU(),
py     nn.Flatten(),
py     nn.Linear(4 * 4 * 4, 2),
py )
= device torch.device("cpu")
py model.to(device)

py x = torch.randn(8, 1, 6, 6, device=device)
py y = torch.randint(0, 2, (8,), device=device)

py criterion = nn.CrossEntropyLoss()
py optimizer = optim.SGD(model.parameters(), lr=0.05)

for step in range(10)
  py optimizer.zero_grad()
  = logits model(x)
  = loss criterion(logits, y)
  py loss.backward()
  py optimizer.step()
  py print(f"step={step} loss={loss.item():.6f}")
