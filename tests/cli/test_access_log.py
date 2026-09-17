from unittest.mock import MagicMock, patch

from free_claude_code.cli.commands import ServerSupervisor
from free_claude_code.config.settings import Settings


def test_server_disables_noisy_http_access_logs() -> None:
    supervisor = ServerSupervisor()
    settings = Settings()
    socket = MagicMock()
    config = MagicMock()
    server = MagicMock()
    app = MagicMock()

    with (
        patch("uvicorn.Config", return_value=config) as config_factory,
        patch(
            "free_claude_code.runtime.bootstrap.build_asgi_app", return_value=app
        ),
        patch("free_claude_code.cli.uvicorn_server.RuntimeServer", return_value=server),
    ):
        server.run.return_value = None
        supervisor._run_bound(
            settings, [socket], open_admin_browser=False, restart_generation=0
        )

    assert config_factory.call_args.kwargs["access_log"] is False
