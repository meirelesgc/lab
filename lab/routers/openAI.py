from fastapi import APIRouter

router = APIRouter(prefix='/openai', tags=['OpenAI'])


@router.get('/')
def home():
    return {'message': 'ola mundo'}
