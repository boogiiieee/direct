import sentry_sdk
import uvicorn
from api.direct_handler import direct_router
from api.service import service_router
from base.exceptions import APIException, ErrorResponse
from configs import APP_PORT, SENTRY_DSN
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

#########################
# BLOCK WITH API ROUTES #
#########################

# create instance of the app
app = FastAPI(title="PYGMA Direct Communication service")

sentry_sdk.init(
    dsn=SENTRY_DSN,
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)


# exceptions
@app.exception_handler(APIException)
async def api_exception_handler(_: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content=ErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.detail,
        ).model_dump(),
    )


# create the instance for the routes
main_api_router = APIRouter()

# set routes to the app instance
main_api_router.include_router(direct_router, prefix="/v1/api/direct", tags=["Direct"])
main_api_router.include_router(service_router, tags=["service"])
app.include_router(main_api_router)

if __name__ == "__main__":
    # run app on the host and port
    config = uvicorn.Config(app, host="0.0.0.0", port=APP_PORT, reload=True)
    server = uvicorn.Server(config)
    server.run()
