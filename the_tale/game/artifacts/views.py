# coding: utf-8
import uuid

from django.core.urlresolvers import reverse

from dext.views import handler, validator, validate_argument
from dext.utils.decorators import nested_commit_on_success
from dext.utils.urls import UrlBuilder

from common.utils.resources import Resource
from common.utils.decorators import login_required
from common.utils.enum import create_enum

from game.map.relations import TERRAIN

from game.artifacts.models import ARTIFACT_RECORD_STATE, RARITY_TYPE
from game.artifacts.relations import ARTIFACT_TYPE
from game.artifacts.prototypes import ArtifactRecordPrototype
from game.artifacts.storage import artifacts_storage
from game.artifacts.forms import ArtifactRecordForm, ModerateArtifactRecordForm


INDEX_ORDER_TYPE = create_enum('INDEX_ORDER_TYPE', (('BY_LEVEL', 'by_level', u'по уровню'),
                                                    ('BY_NAME', 'by_name', u'по имени'),))

def argument_to_artifact_type(value): return ARTIFACT_TYPE(int(value))


class ArtifactResourceBase(Resource):

    @validate_argument('artifact', ArtifactRecordPrototype.get_by_id, 'artifacts', u'Запись об артефакте не найдена')
    def initialize(self, artifact=None, *args, **kwargs):
        super(ArtifactResourceBase, self).initialize(*args, **kwargs)
        self.artifact = artifact

        self.can_create_artifact = self.account.has_perm('artifacts.create_artifactrecord')
        self.can_moderate_artifact = self.account.has_perm('artifacts.moderate_artifactrecord')


class GuideArtifactResource(ArtifactResourceBase):


    @validator(code='artifacts.artifact_disabled', message=u'артефакт находится вне игры', status_code=404)
    def validate_artifact_disabled(self, *args, **kwargs):
        return not self.artifact.state.is_disabled or self.can_create_artifact or self.can_moderate_artifact


    @validate_argument('state', ARTIFACT_RECORD_STATE, 'artifacts', u'неверное состояние записи об артефакте')
    @validate_argument('rarity', RARITY_TYPE, 'artifacts', u'неверный тип редкости артефакта')
    @validate_argument('type', argument_to_artifact_type, 'artifacts', u'неверный тип артефакта')
    @validate_argument('order_by', INDEX_ORDER_TYPE, 'artifacts', u'неверный тип сортировки')
    @handler('', method='get')
    def index(self,
              state=ARTIFACT_RECORD_STATE(ARTIFACT_RECORD_STATE.ENABLED),
              type=None, # pylint: disable=W0622
              rarity=None,
              order_by=INDEX_ORDER_TYPE(INDEX_ORDER_TYPE.BY_NAME)):

        artifacts = artifacts_storage.all()

        if not self.can_create_artifact and not self.can_moderate_artifact:
            artifacts = filter(lambda artifact: artifact.state.is_enabled, artifacts) # pylint: disable=W0110

        is_filtering = False

        if state is not None:
            if not state.is_enabled: # if not default
                is_filtering = True
            artifacts = filter(lambda artifact: artifact.state == state, artifacts) # pylint: disable=W0110

        if rarity is not None:
            is_filtering = True
            artifacts = filter(lambda artifact: artifact.rarity == rarity, artifacts) # pylint: disable=W0110

        if type is not None:
            is_filtering = True
            artifacts = filter(lambda artifact: artifact.type == type, artifacts) # pylint: disable=W0110

        if order_by.is_by_name:
            artifacts = sorted(artifacts, key=lambda artifact: artifact.name)
        elif order_by.is_by_level:
            artifacts = sorted(artifacts, key=lambda artifact: artifact.level)

        url_builder = UrlBuilder(reverse('guide:artifacts:'), arguments={ 'state': state.value if state else None,
                                                                          'rarity': rarity.value if rarity else None,
                                                                          'type': type.value if type else None,
                                                                          'order_by': order_by.value})
        return self.template('artifacts/index.html',
                             {'artifacts': artifacts,
                              'is_filtering': is_filtering,
                              'ARTIFACT_RECORD_STATE': ARTIFACT_RECORD_STATE,
                              'TERRAIN': TERRAIN,
                              'RARITY_TYPE': RARITY_TYPE,
                              'ARTIFACT_TYPE': ARTIFACT_TYPE,
                              'state': state,
                              'rarity': rarity,
                              'type': type,
                              'order_by': order_by,
                              'INDEX_ORDER_TYPE': INDEX_ORDER_TYPE,
                              'url_builder': url_builder,
                              'section': 'artifacts'} )

    @validate_artifact_disabled()
    @handler('#artifact', name='show', method='get')
    def show(self):
        return self.template('artifacts/show.html', {'artifact': self.artifact,
                                                     'section': 'artifacts'})

    @validate_artifact_disabled()
    @handler('#artifact', 'info', method='get')
    def show_dialog(self):
        return self.template('artifacts/info.html', {'artifact': self.artifact})


class GameArtifactResource(ArtifactResourceBase):

    @validator(code='artifacts.create_artifact_rights_required', message=u'Вы не можете создавать артефакты')
    def validate_create_rights(self, *args, **kwargs): return self.can_create_artifact

    @validator(code='artifacts.moderate_artifact_rights_required', message=u'Вы не можете принимать артефакты в игру')
    def validate_moderate_rights(self, *args, **kwargs): return self.can_moderate_artifact

    @validator(code='artifacts.disabled_state_required', message=u'Для проведения этой операции артефакт должен быть убран из игры')
    def validate_disabled_state(self, *args, **kwargs): return self.artifact.state.is_disabled

    @login_required
    @validate_create_rights()
    @handler('new', method='get')
    def new(self):
        return self.template('artifacts/new.html', {'form': ArtifactRecordForm()})

    @login_required
    @validate_create_rights()
    @nested_commit_on_success
    @handler('create', method='post')
    def create(self):

        form = ArtifactRecordForm(self.request.POST)

        if not form.is_valid():
            return self.json_error('artifacts.create.form_errors', form.errors)

        artifact = ArtifactRecordPrototype.create(uuid=uuid.uuid4().hex,
                                                  level=form.c.level,
                                                  name=form.c.name,
                                                  description=form.c.description,
                                                  type_=form.c.type,
                                                  rarity=form.c.rarity,
                                                  editor=self.account,
                                                  state=ARTIFACT_RECORD_STATE.DISABLED,
                                                  mob=form.c.mob)
        return self.json_ok(data={'next_url': reverse('guide:artifacts:show', args=[artifact.id])})


    @login_required
    @validate_disabled_state()
    @validate_create_rights()
    @handler('#artifact', 'edit', name='edit', method='get')
    def edit(self):
        form = ArtifactRecordForm(initial={'name': self.artifact.name,
                                           'level': self.artifact.level,
                                           'type': self.artifact.type.value,
                                           'rarity': self.artifact.type.value,
                                           'description': self.artifact.description,
                                           'mob': self.artifact.mob.id if self.artifact.mob is not None else None})

        return self.template('artifacts/edit.html', {'artifact': self.artifact,
                                                     'form': form} )

    @login_required
    @validate_disabled_state()
    @validate_create_rights()
    @nested_commit_on_success
    @handler('#artifact', 'update', name='update', method='post')
    def update(self):

        form = ArtifactRecordForm(self.request.POST)

        if not form.is_valid():
            return self.json_error('artifacts.update.form_errors', form.errors)

        self.artifact.update_by_creator(form, editor=self.account)

        return self.json_ok(data={'next_url': reverse('guide:artifacts:show', args=[self.artifact.id])})

    @login_required
    @validate_moderate_rights()
    @handler('#artifact', 'moderate', name='moderate', method='get')
    def moderation_page(self):
        form = ModerateArtifactRecordForm(initial={'name': self.artifact.name,
                                                   'level': self.artifact.level,
                                                   'type': self.artifact.type.value,
                                                   'rarity': self.artifact.type.value,
                                                   'description': self.artifact.description,
                                                   'uuid': self.artifact.uuid,
                                                   'name_forms': self.artifact.name_forms.serialize(),
                                                   'approved': self.artifact.state.is_enabled,
                                                   'mob': self.artifact.mob.id if self.artifact.mob is not None else None})

        return self.template('artifacts/moderate.html', {'artifact': self.artifact,
                                                         'form': form} )

    @login_required
    @validate_moderate_rights()
    @nested_commit_on_success
    @handler('#artifact', 'moderate', name='moderate', method='post')
    def moderate(self):
        form = ModerateArtifactRecordForm(self.request.POST)

        if not form.is_valid():
            return self.json_error('artifacts.moderate.form_errors', form.errors)

        self.artifact.update_by_moderator(form, editor=self.account)

        return self.json_ok(data={'next_url': reverse('guide:artifacts:show', args=[self.artifact.id])})
