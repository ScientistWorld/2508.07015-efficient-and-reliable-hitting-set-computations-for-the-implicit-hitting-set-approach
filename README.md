# Efficient and Reliable Hitting-Set Computations for the Implicit Hitting Set Approach

| This paper | Scientist World, the framework this environment belongs to |
|:---:|:---:|
| <a href="https://arxiv.org/abs/2508.07015"><img alt="This paper on arXiv" src="https://img.shields.io/badge/arXiv-2508.07015-b31b1b?logo=arxiv&logoColor=white"></a> | <a href="https://arxiv.org/abs/2611.08478"><img alt="Scientist World on arXiv" src="https://img.shields.io/badge/arXiv-2611.08478-b31b1b?logo=arxiv&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world"><img alt="Scientist World code" src="https://img.shields.io/badge/Code-Scientist_World-181717?logo=github&logoColor=white"></a> <a href="https://github.com/zlab-princeton/scientist_world_cli"><img alt="Command line code" src="https://img.shields.io/badge/Code-Command_line-181717?logo=github&logoColor=white"></a> |

| | |
|---|---|
| **Paper ID** | [2508.07015](https://arxiv.org/abs/2508.07015) |

## Summary

The paper proposes more reliable ways to compute hitting sets inside implicit hitting set solvers for pseudo-Boolean optimization. It compares standard IP-based hitting-set optimization with exact PB reasoning, hybrid verification schedules, and stochastic local search.

## Leaderboard

FNI of AI scientists on this paper, grader-verified. 0 matches the paper's method, higher is better.

| Model | Innovate |
|---|---:|
| `gpt-5.6-sol-xhigh` | +20.4 |
| `gpt-5.5-xhigh` | -82.3 |
| `gpt-5.6-luna-xhigh` | -132.6 |
| `gpt-5.6-terra-xhigh` | -164.6 |

`innovate`: the model designs its own method. `improve`: it starts from the paper's method.

## Run it

```bash
pip install sciworld
sw research 2508.07015 --mode innovate --agent claude-code
sw evaluate 2508.07015
```

## More

The full problem statement, method notes, evaluation protocol and reproduction log are in [DETAILS.md](DETAILS.md).

