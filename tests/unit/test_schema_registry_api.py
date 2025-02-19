from aiohttp.test_utils import TestClient, TestServer
from karapace.config import DEFAULTS
from karapace.rapu import HTTPResponse
from karapace.schema_registry_apis import KarapaceSchemaRegistryController
from unittest.mock import ANY, Mock, patch, PropertyMock

import asyncio


async def test_forward_when_not_ready():
    with patch("karapace.schema_registry_apis.aiohttp.ClientSession") as client_session_class, patch(
        "karapace.schema_registry_apis.KarapaceSchemaRegistry"
    ) as schema_registry_class:
        client_session = Mock()
        client_session_class.return_value = client_session

        schema_reader_mock = Mock()
        ready_property_mock = PropertyMock(return_value=False)
        schema_registry = Mock()
        type(schema_reader_mock).ready = ready_property_mock
        schema_registry.schema_reader = schema_reader_mock
        schema_registry_class.return_value = schema_registry

        get_master_future = asyncio.Future()
        get_master_future.set_result((False, "http://primary-url"))
        schema_registry.get_master.return_value = get_master_future

        close_future_result = asyncio.Future()
        close_future_result.set_result(True)
        close_func = Mock()
        close_func.return_value = close_future_result
        schema_registry.close = close_func
        client_session.close = close_func

        controller = KarapaceSchemaRegistryController(config=DEFAULTS)
        mock_forward_func_future = asyncio.Future()
        mock_forward_func_future.set_exception(HTTPResponse({"mock": "response"}))
        mock_forward_func = Mock()
        mock_forward_func.return_value = mock_forward_func_future
        controller._forward_request_remote = mock_forward_func  # pylint: disable=protected-access

        test_server = TestServer(controller.app)
        async with TestClient(test_server) as client:
            await client.get("/schemas/ids/1", headers={"Content-Type": "application/json"})

            ready_property_mock.assert_called_once()
            schema_registry.get_master.assert_called_once()
            mock_forward_func.assert_called_once_with(
                request=ANY, body=None, url="http://primary-url/schemas/ids/1", content_type="application/json", method="GET"
            )
