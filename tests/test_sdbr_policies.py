import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"sdbr-mini-usine"/"scripts"))
from policies import select_batch


@pytest.mark.parametrize("rule,expected",[("fifo",[0]),("family_fifo",[1,3]),("batch_fifo",[0,2])])
def test_local_strategy_cannot_read_deadline(rule,expected):
    def forbidden(_):
        raise AssertionError("consultation de la date promise")
    result=select_batch([(i,i) for i in range(4)], ["A","B","A","B"].__getitem__,
                        forbidden,"B",10,2,3,rule)
    assert [i for _,i in result]==expected
