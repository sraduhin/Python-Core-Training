from contextlib import asynccontextmanager


@asynccontextmanager
async def opened_resource(opener):
    resource = await opener()
    try:
        yield resource
    finally:
        await resource.aclose()
