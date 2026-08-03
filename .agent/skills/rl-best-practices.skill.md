---
name: rl-best-practices
description: Enforces best practices for Reinforcement Learning environments, agents, and training loops.
---

# Reinforcement Learning (RL) Best Practices Skill

When developing the RL optimization framework for the Digital Twin, ensure the implementation is robust, reproducible, and scalable.

## 1. Environment Design (Gymnasium)
- **Standardization**: Implement environments subclassing `gymnasium.Env`.
- **Observation Space**: Normalize observations (e.g., to `[-1, 1]`). Define limits clearly in `spaces.Box`.
- **Action Space**: Keep actions normalized. Scale actions inside the `step()` function before applying them to the physics model.
- **Reward Function**: 
  - Ensure rewards are scaled appropriately.
  - Avoid sparse rewards if possible; use reward shaping to guide the agent toward the goal (e.g., maximizing hydrogen yield while minimizing grid cost).

## 2. Reproducibility
- **Seeding**: Provide mechanisms to seed the environment, action spaces, and the RL algorithm identically for reproducible runs.
- **Hyperparameter Tracking**: Log all hyperparameters, network architectures, and environment configs using tools like Weights & Biases (`wandb`), MLflow, or TensorBoard.

## 3. Training & Evaluation
- **Vectorization**: Support vectorized environments (`SyncVectorEnv` or `AsyncVectorEnv`) to speed up data collection.
- **Evaluation Callbacks**: Separate training and evaluation. Evaluate the agent deterministically on a separate validation environment at regular intervals.
- **Checkpointing**: Save model checkpoints frequently.

## 4. Digital Twin Integration
- **Simulation Speed**: Ensure the `step()` function of the digital twin is highly optimized (e.g., using `numba` or vectorized `numpy` operations) as it will be called millions of times.
- **State Synchrony**: Provide a method to synchronize the RL environment state with real-time sensor data from the physical twin.
