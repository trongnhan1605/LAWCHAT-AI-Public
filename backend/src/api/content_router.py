from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.schemas.admin_schema import ContentArticleItem, LawyerProfileItem
from src.schemas.base import BaseResponse
from src.schemas.knowledge_schema import CategoryItem
from src.services.admin_service import admin_service


class HomeMenuItem(BaseModel):
    label: str
    href: str


class HomeContentPayload(BaseModel):
    menu: list[HomeMenuItem]
    categories: list[CategoryItem]
    articles: list[ContentArticleItem]
    lawyers: list[LawyerProfileItem]


class HomeContentResponse(BaseResponse[HomeContentPayload]):
    pass


router = APIRouter(prefix="/content", tags=["content"])

HOME_MENU = [
    HomeMenuItem(label="Tìm luật sư", href="#find-lawyer"),
    HomeMenuItem(label="Tư vấn pháp luật", href="#ask-lawchat"),
    HomeMenuItem(label="Dịch vụ pháp lý", href="#legal-services"),
    HomeMenuItem(label="Đặt câu hỏi miễn phí", href="#ask-lawchat"),
    HomeMenuItem(label="Đăng nhập", href="/login"),
]


@router.get("/home", response_model=HomeContentResponse)
def home_content(db: Session = Depends(get_db)) -> HomeContentResponse:
    articles = [
        ContentArticleItem.model_validate(item)
        for item in admin_service.list_content_articles(db)
        if item.is_active
    ][:6]
    lawyers = [
        LawyerProfileItem.model_validate(item)
        for item in admin_service.list_lawyer_profiles(db)
        if item.is_active
    ][:6]
    categories = [
        CategoryItem.model_validate(item)
        for item in admin_service.list_categories(db)
        if item.is_active
    ]
    payload = HomeContentPayload(menu=HOME_MENU, categories=categories, articles=articles, lawyers=lawyers)
    return HomeContentResponse(success=True, message="Home content fetched", data=payload)
