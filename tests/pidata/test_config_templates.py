import pytest
import yaml

from pidata.config_templates import (
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    render_agent_yml,
    render_datus_config_yml,
)


def test_render_agent_yml_starrocks():
    cfg = yaml.safe_load(render_agent_yml("starrocks"))
    agent = cfg["agent"]
    assert agent["providers"]["deepseek"]["api_key"] == "${DEEPSEEK_API_KEY}"
    assert agent["date_parsing"]["language"] == "zh"
    ds = agent["services"]["datasources"]["edw_starrocks"]
    assert ds == {
        "type": "starrocks",
        "host": "${EDW_HOST}",
        "port": "${EDW_PORT}",
        "username": "${EDW_USER}",
        "password": "${EDW_PASSWORD}",
        "database": "${EDW_DATABASE}",
    }


def test_render_agent_yml_doris_uses_internal_catalog():
    cfg = yaml.safe_load(render_agent_yml("doris"))
    ds = cfg["agent"]["services"]["datasources"]["edw_doris"]
    assert ds["type"] == "doris"
    assert ds["catalog"] == "internal"
    assert "edw_starrocks" not in cfg["agent"]["services"]["datasources"]


def test_render_agent_yml_rejects_unknown_type():
    with pytest.raises(ValueError, match="edw_type"):
        render_agent_yml("mysql")


def test_render_datus_config_yml_starrocks():
    cfg = yaml.safe_load(render_datus_config_yml("starrocks"))
    assert cfg["target"] == {"provider": DEFAULT_PROVIDER, "model": DEFAULT_MODEL}
    assert cfg["default_datasource"] == "edw_starrocks"
    assert cfg["project_name"] == "pidataagent"


def test_render_datus_config_yml_doris():
    cfg = yaml.safe_load(render_datus_config_yml("doris", model="deepseek-v4-flash"))
    assert cfg["default_datasource"] == "edw_doris"
    assert cfg["target"]["model"] == "deepseek-v4-flash"
