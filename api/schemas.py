from typing import Optional

from pydantic import BaseModel

#########################
# BLOCK WITH API MODELS #
#########################

#####################
#   THREAD MESSAGE  #
#####################


class DataThreadMessageRequest(BaseModel):
    instagram_id_from_instagrapi: Optional[str]
    instagram_id_from_official_graph_api: Optional[str]
    instagram_user_id_from_instagrapi: Optional[str]
    instagram_user_id_from_official_graph_api: Optional[str]
    created_at: float
    sender: str
    item_type: str
    text: Optional[str]
    link: Optional[str]


class ThreadMessageRequest(BaseModel):
    thread_id: int
    messages: list[DataThreadMessageRequest]


class DataThreadMessage(DataThreadMessageRequest):
    id: int
    thread_id: int


class ThreadMessageResponse(BaseModel):
    success: bool
    data: list[DataThreadMessage] = None
    error: Optional[str] = None


#####################
# GENERATED MESSAGE #
#####################


class DataGeneratedMessage(BaseModel):
    id: int
    thread_id: int
    text: str
    status: str
    thread_instagram_id_from_instagrapi: Optional[str]
    thread_instagram_id_from_official_graph_api: Optional[str]
    recipient_instagram_id_from_instagrapi: Optional[str]
    recipient_instagram_id_from_official_graph_api: Optional[str]
    recipient_instagram_username: str


#####################
#       BLOGGER     #
#####################


class DataBlogger(BaseModel):
    id: int
    instagram_login: str
    status: str
    can_use_official_graph_api: bool
    facebook_page_id: Optional[str]
    facebook_page_access_token: Optional[str]


class DataBloggerWithGeneratedMessages(DataBlogger):
    messages: list[DataGeneratedMessage] = None


#####################
#      THREAD       #
#####################


class DataThreadRequest(BaseModel):
    instagram_id_from_instagrapi: Optional[str]
    instagram_id_from_official_graph_api: Optional[str]
    thread_to_user_id_from_instagrapi: Optional[str]
    thread_to_user_id_from_official_graph_api: Optional[str]
    thread_to_username: str
    messages: list[DataThreadMessageRequest]


class DataThread(DataThreadRequest):
    id: int
    messages: list[DataThreadMessage] = None
