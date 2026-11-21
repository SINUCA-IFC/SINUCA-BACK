import logging
from functools import partial

from django.db import transaction

from core.services.push import send_push_event

logger = logging.getLogger(__name__)


def deliver_push_event(payload, *, excluded_endpoint=None, user_ids=None):
    """Uma falha de notificação não pode desfazer a ação já salva."""
    try:
        return send_push_event(payload, excluded_endpoint=excluded_endpoint, user_ids=user_ids)
    except Exception:
        logger.exception('Falha no envio do evento push %s.', payload.get('event'))
        return 0


def schedule_push_event(payload, *, excluded_endpoint=None, user_ids=None):
    transaction.on_commit(
        partial(
            deliver_push_event,
            payload,
            excluded_endpoint=excluded_endpoint,
            user_ids=user_ids,
        )
    )


def post_payload(post):
    return {
        'event': 'post_created',
        'title': 'Nova postagem no mural',
        'body': post.title,
        'data': {'post_id': post.pk, 'url': '/mural'},
    }


def task_payload(task, event):
    return {
        'event': event,
        'title': 'Tarefa atribuída a você' if event == 'task_assigned' else 'O prazo da tarefa passou',
        'body': task.title,
        'data': {'task_id': task.pk, 'url': f'/delegacao?task={task.pk}'},
    }
