
[🤗hugging face deep reinforcement learning course](https://huggingface.co/learn/deep-rl-course/unit0/introduction?fw=pt)
# Introduction

# What is Reinforcement Learning


> Reinforcement learning is a framework for solving control tasks (also called decision problems) by building agents that learn from the environment by interacting with it through trial and error and receiving rewards (positive or negative) as unique feedback.
  
# The Reinforcement Learning Framework

![Reinforcement Learning Framework](https://huggingface.co/datasets/huggingface-deep-rl-course/course-images/resolve/main/en/unit1/RL_process.jpg)


_reward hypothesis_: a goal can be described as the **maximization of the expected cumulative reward**.

> agent needs only the current state to decide what action to take and not the history of all the states and actions they took before.


## The RL Process
## The reward hypothesis: the central idea of Reinforcement Learning

## Markov Property

## Observations/States Space

The difference between state and observation.

  
## Action Space

## Rewards and the discounting
![](https://huggingface.co/datasets/huggingface-deep-rl-course/course-images/resolve/main/en/unit1/rewards_4.jpg)


  

  

# Type of tasks

![xx](https://huggingface.co/datasets/huggingface-deep-rl-course/course-images/resolve/main/en/unit1/tasks.jpg)

  
# The Exploration/Exploitation trade-off
![](https://duke-1258882975.cos.ap-guangzhou.myqcloud.com/picture/20251223094724711.png)


# Two main approaches for solving RL problems

## The Policy π: the agent’s brain


## Policy-Based Methods

![](https://duke-1258882975.cos.ap-guangzhou.myqcloud.com/picture/20251223100335614.png)


![](https://huggingface.co/datasets/huggingface-deep-rl-course/course-images/resolve/main/en/unit1/pbm_2.jpg)

## Value-based methods


# The “Deep” in Deep Reinforcement Leaning

# Summary

# Glossary
This is a community-created glossary. Contributions are welcome!

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#agent)Agent

An agent learns to **make decisions by trial and error, with rewards and punishments from the surroundings**.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#environment)Environment

An environment is a simulated world **where an agent can learn by interacting with it**.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#markov-property)Markov Property

It implies that the action taken by our agent is **conditional solely on the present state and independent of the past states and actions**.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#observationsstate)Observations/State

- **State**: Complete description of the state of the world.
- **Observation**: Partial description of the state of the environment/world.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#actions)Actions

- **Discrete Actions**: Finite number of actions, such as left, right, up, and down.
- **Continuous Actions**: Infinite possibility of actions; for example, in the case of self-driving cars, the driving scenario has an infinite possibility of actions occurring.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#rewards-and-discounting)Rewards and Discounting

- **Rewards**: Fundamental factor in RL. Tells the agent whether the action taken is good/bad.
- RL algorithms are focused on maximizing the **cumulative reward**.
- **Reward Hypothesis**: RL problems can be formulated as a maximisation of (cumulative) return.
- **Discounting** is performed because rewards obtained at the start are more likely to happen as they are more predictable than long-term rewards.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#tasks)Tasks

- **Episodic**: Has a starting point and an ending point.
- **Continuous**: Has a starting point but no ending point.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#exploration-vs-exploitation-trade-off)Exploration v/s Exploitation Trade-Off

- **Exploration**: It’s all about exploring the environment by trying random actions and receiving feedback/returns/rewards from the environment.
- **Exploitation**: It’s about exploiting what we know about the environment to gain maximum rewards.
- **Exploration-Exploitation Trade-Off**: It balances how much we want to **explore** the environment and how much we want to **exploit** what we know about the environment.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#policy)Policy

- **Policy**: It is called the agent’s brain. It tells us what action to take, given the state.
- **Optimal Policy**: Policy that **maximizes** the **expected return** when an agent acts according to it. It is learned through _training_.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#policy-based-methods)Policy-based Methods:

- An approach to solving RL problems.
- In this method, the Policy is learned directly.
- Will map each state to the best corresponding action at that state. Or a probability distribution over the set of possible actions at that state.

### [](https://huggingface.co/learn/deep-rl-course/unit1/glossary#value-based-methods)Value-based Methods:

- Another approach to solving RL problems.
- Here, instead of training a policy, we train a **value function** that maps each state to the expected value of being in that state.