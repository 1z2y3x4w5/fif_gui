import pytest
import importlib

FiFWebClient = importlib.import_module('connector.FiFWebClient').FiFWebClient

def test_rule_match():
    fif = FiFWebClient()
    # 模拟规则判断（需根据实际 should_skip/level_type_rules 逻辑扩展）
    # 这里只做接口可调用性测试
    assert hasattr(fif, 'get_user_info')
    assert hasattr(fif, 'get_task_list')
    assert hasattr(fif, 'get_level_answer')
