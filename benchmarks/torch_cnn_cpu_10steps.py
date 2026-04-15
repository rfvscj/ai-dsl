import torch
import torch.nn as nn
import torch.optim as optim


torch.manual_seed(0)

model = nn.Sequential(
    nn.Conv2d(1, 4, kernel_size=3),
    nn.ReLU(),
    nn.Flatten(),
    nn.Linear(4 * 4 * 4, 2),
)
device = torch.device("cpu")
model.to(device)

x = torch.randn(8, 1, 6, 6, device=device)
y = torch.randint(0, 2, (8,), device=device)

criterion = nn.CrossEntropyLoss()
optimizer = optim.SGD(model.parameters(), lr=0.05)

for step in range(10):
    optimizer.zero_grad()
    logits = model(x)
    loss = criterion(logits, y)
    loss.backward()
    optimizer.step()
    print(f"step={step} loss={loss.item():.6f}")
