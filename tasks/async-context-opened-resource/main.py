from contextlib import asynccontextmanager


@asynccontextmanager
async def opened_resource(opener):
    try:
        resource = await opener()
    except Exception as e:
        raise TypeError(e)
    try:
        yield resource
    finally:
        await resource.aclose()
