from .greedy import GreedyAgent
from .minimax import MinimaxAgent
from .mcts import MCTSAgent

AGENTS = {"Minimax": MinimaxAgent, "MCTS": MCTSAgent, "Greedy": GreedyAgent}


def make(name, seed=None):
    return AGENTS[name](seed=seed)
