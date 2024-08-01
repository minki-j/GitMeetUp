from varname import nameof as n
from ..state_schema import State


def have_enough_hypotheses(state: State) -> bool:
    hypotheses = state["final_hypotheses"]
    if not hypotheses:
        print("No hypotheses found yet, continue collecting")

    print(f"collected {len(hypotheses)} hypotheses so far")

    if len(hypotheses) >= 2:
        return "__end__"
    else:
        return "find_next_hypothesis"
