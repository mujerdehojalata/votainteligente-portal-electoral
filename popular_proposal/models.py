# coding=utf-8
from __future__ import unicode_literals

from django.db import models
from picklefield.fields import PickledObjectField
from django.contrib.auth.models import User
from djchoices import DjangoChoices, ChoiceItem
from votainteligente.send_mails import send_mail
from django.utils.encoding import python_2_unicode_compatible
from django.contrib.sites.models import Site
from autoslug import AutoSlugField
from django.core.urlresolvers import reverse
from backend_citizen.models import Organization
from votainteligente.open_graph import OGPMixin
from elections.models import Candidate, Area
from django.db.models import Count
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import get_template
from PIL import Image, ImageDraw, ImageFont
from model_utils.managers import InheritanceQuerySetMixin
import textwrap
from django.contrib.contenttypes.models import ContentType


class NeedingModerationManager(models.Manager):
    def get_queryset(self, *args, **kwargs):
        qs = super(NeedingModerationManager, self).get_queryset(*args, **kwargs)
        qs = qs.filter(status=ProposalTemporaryData.Statuses.InOurSide)
        return qs


class ProposalCreationMixin(object):
    def determine_kwargs(self, **kwargs):
            model = kwargs.pop('model_class', self.__class__)
            for f in model._meta.fields:
                if f.name in kwargs['data'].keys():
                    kwargs[f.name] = kwargs['data'].pop(f.name)
            return kwargs


@python_2_unicode_compatible
class ProposalTemporaryData(models.Model, ProposalCreationMixin):
    class Statuses(DjangoChoices):
        InOurSide = ChoiceItem('in_our_side')
        InTheirSide = ChoiceItem('in_their_side')
        Rejected = ChoiceItem('rejected')
        Accepted = ChoiceItem('accepted')
    proposer = models.ForeignKey(User, related_name='temporary_proposals')
    area = models.ForeignKey(Area, related_name='temporary_proposals', null=True, blank=True)
    join_advocacy_url = models.URLField(null=True, blank=True)
    data = PickledObjectField()
    rejected = models.BooleanField(default=False)
    rejected_reason = models.TextField(null=True,
                                       blank=True)
    organization = models.ForeignKey(Organization,
                                     related_name='temporary_proposals',
                                     null=True,
                                     blank=True,
                                     default=None)
    comments = PickledObjectField()
    status = models.CharField(max_length=16,
                              choices=Statuses.choices,
                              validators=[Statuses.validator],
                              default=Statuses.InOurSide)
    overall_comments = models.CharField(max_length=512,
                                        blank=True,
                                        null=True,
                                        default="")
    is_local_meeting = models.BooleanField(default=False)
    generated_at = models.ForeignKey(Area,
                                     null=True,
                                     blank=True)
    created = models.DateTimeField(auto_now_add=True,
                                   blank=True,
                                   null=True)
    updated = models.DateTimeField(auto_now=True,
                                   blank=True,
                                   null=True)

    needing_moderation = NeedingModerationManager()
    objects = models.Manager()


    def save(self, *args, **kwargs):
        if not self.comments:
            self.comments = {}
        for key in self.data.keys():
            if key not in self.comments.keys():
                self.comments[key] = ''
        return super(ProposalTemporaryData, self).save(*args, **kwargs)

    def notify_new(self):
        site = Site.objects.get_current()
        mail_context = {
            'area': self.area,
            'temporary_data': self,
            'site': site,
        }
        if self.proposer.email:
            send_mail(mail_context, 'new_temporary_proposal',
                      to=[self.proposer.email])

    def create_proposal(self, moderator=None):
        self.status = ProposalTemporaryData.Statuses.Accepted
        self.save()
        title = self.get_title()
        clasification = self.data.get('clasification', '')
        org_id = self.data.pop('organization', None)

        creation_kwargs = self.determine_kwargs(title=title,
                                                clasification=clasification,
                                                area=self.area,
                                                proposer=self.proposer,
                                                data=self.data,
                                                temporary=self)
        popular_proposal = PopularProposal(**creation_kwargs)
        if org_id:
            enrollment = self.proposer.enrollments.get(organization__id=org_id)
            popular_proposal.organization = enrollment.organization
        popular_proposal.save()
        site = Site.objects.get_current()
        mail_context = {
            'area': self.area,
            'temporary_data': self,
            'moderator': moderator,
            'site': site,
        }
        send_mail(mail_context, 'popular_proposal_accepted', to=[self.proposer.email])
        return popular_proposal

    def reject(self, reason, moderator=None):
        self.rejected_reason = reason
        self.status = ProposalTemporaryData.Statuses.Rejected
        self.save()
        site = Site.objects.get_current()
        mail_context = {
            'area': self.area,
            'temporary_data': self,
            'moderator': moderator,
            'site': site,
        }
        send_mail(mail_context, 'popular_proposal_rejected',
                  to=[self.proposer.email])

    def get_title(self):
        return self.data.get('title', u'')

    def __str__(self):
        return self.get_title()


class ProposalsManager(models.Manager):
    def get_queryset(self):
        qs = super(ProposalsManager, self).get_queryset()
        if settings.EXCLUDED_PROPOSALS_APPS:
            qs = qs.exclude(content_type__app_label__in=settings.EXCLUDED_PROPOSALS_APPS)
        qs = qs.exclude(is_reported=True)
        return qs


class ProposalQuerySet(InheritanceQuerySetMixin, models.QuerySet):
    def by_likers(self, *args, **kwargs):
        return self.order_by('-num_likers', 'proposer__profile__is_organization')


class ProposalsOrderedManager(ProposalsManager):
    def get_queryset(self):
        qs = ProposalQuerySet(self.model, using=self._db).exclude(is_reported=True)
        qs = qs.annotate(num_likers=Count('likers'))
        qs = qs.select_subclasses()
        return qs


@python_2_unicode_compatible
class PopularProposal(models.Model, OGPMixin):
    title = models.CharField(max_length=255, default='')
    slug = AutoSlugField(populate_from='title', unique=True)
    proposer = models.ForeignKey(User, related_name='proposals')
    area = models.ForeignKey(Area, related_name='proposals', null=True, blank=True)
    join_advocacy_url = models.URLField(null=True, blank=True)
    data = PickledObjectField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)
    temporary = models.OneToOneField(ProposalTemporaryData,
                                     related_name='created_proposal',
                                     blank=True,
                                     null=True,
                                     default=None)
    likers = models.ManyToManyField(User, through='ProposalLike')
    organization = models.ForeignKey(Organization,
                                     related_name='popular_proposals',
                                     null=True)
    background = models.TextField(null=True, blank=True, help_text=_(u"Antecedentes sobre tu propuesta"))
    contact_details = models.TextField(null=True,
                                       blank=True,
                                       help_text=_(u'¿Cómo te pueden contactar? Esta información es pública.'))
    document = models.FileField(upload_to='uploads/proposal/backgrounds/%Y/%m/%d/',
                                help_text=_(u'¿Tienes algún documento para complementar tu propuesta?'),
                                null=True,
                                blank=True)
    image = models.ImageField(upload_to='proposals/image/',
                              max_length=512,
                              null=True,
                              blank=True)
    clasification = models.CharField(blank=True, null=True, max_length=255)
    for_all_areas = models.BooleanField(default=False)
    generated_at = models.ForeignKey(Area,
                                     related_name='proposals_generated_here',
                                     null=True,
                                     blank=True)
    is_local_meeting = models.BooleanField(default=False)
    is_reported = models.BooleanField(default=False)

    content_type = models.ForeignKey(ContentType, null=True)
    featured = models.BooleanField(default=False)

    ogp_enabled = True

    ordered = ProposalsOrderedManager.from_queryset(ProposalQuerySet)()
    objects = ProposalsManager()
    all_objects = models.Manager()

    card_template = "popular_proposal/popular_proposal_card.html"

    class Meta:
        ordering = ['-featured' ,'for_all_areas', '-created']
        verbose_name = _(u'Propuesta Ciudadana')
        verbose_name_plural = _(u'Propuestas Ciudadanas')

    def __str__(self):
        return self.title

    def ogp_title(self):
        return u'¡Ingresa a votainteligente.cl y apoya esta propuesta!'

    def save(self, *args, **kwargs):
        created = self.pk is not None
        if not created:
            content_type = ContentType.objects.get_for_model(self.__class__)
            self.content_type = content_type
        super(PopularProposal, self).save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse('popular_proposals:detail', kwargs={'slug': self.slug})

    def get_short_url(self):
        return reverse('popular_proposals:short_detail', kwargs={'pk': self.pk})

    def generate_og_image(self):
        base = Image.open('votai_general_theme/static/img/plantilla.png').convert('RGBA')

        montserrat_n_propuesta = ImageFont.truetype("votai_general_theme/static/fonts/Montserrat-Bold.ttf", 16)
        arvo_titulo = ImageFont.truetype("votai_general_theme/static/fonts/Arvo-Bold.ttf", 60)
        montserrat_autor = ImageFont.truetype("votai_general_theme/static/fonts/Montserrat-Bold.ttf", 22)

        txt = Image.new('RGBA', base.size, (122,183,255,0))

        d = ImageDraw.Draw(txt)
        n_propuesta = u"Propuesta N º"+ unicode(self.id)
        n_propuesta = n_propuesta.upper()
        d.multiline_text((81,95), n_propuesta, font=montserrat_n_propuesta, fill=(122,183,255,255))

        lines = textwrap.wrap(self.title, width=30)
        max_lines = 5
        if len(lines) > max_lines:
            last_line = lines[max_lines - 1] + u'...'
            lines = lines[0:max_lines]
            lines[max_lines - 1] = last_line

        title = '\n'.join(lines)

        d.multiline_text((81,133), title, font=arvo_titulo, fill=(255,255,255,255))

        proposer_name = self.proposer.get_full_name() or self.proposer.username
        propuesta_de = u"Una propuesta de " + proposer_name
        propuesta_de = propuesta_de.upper()
        d.multiline_text((81,471), propuesta_de, font=montserrat_autor, fill=(255,255,255,255))
        out = Image.alpha_composite(base, txt)

        return out

    def ogp_image(self):
        site = Site.objects.get_current()
        image_url = reverse('popular_proposals:og_image',
                            kwargs={'slug': self.slug})
        url = "http://%s%s" % (site.domain,
                               image_url)
        return url

    def display_card(self, context={}):
        context['proposal'] = self
        return get_template(self.card_template).render(context)

    @property
    def card(self):
        return self.display_card({})

    @property
    def data_as_text(self):
        from popular_proposal.forms.form_texts import SEARCH_ELEMENTS_FROM_DATA
        text = u""
        for key in SEARCH_ELEMENTS_FROM_DATA:
            text += u"\n" + self.data.get(key, "")
        return text.strip()

    @property
    def sponsoring_orgs(self):
        return self.likers.filter(profile__is_organization=True)

    def notify_candidates_of_new(self):
        if not (settings.NOTIFY_CANDIDATES and settings.NOTIFY_CANDIDATES_OF_NEW_PROPOSAL):
            return
        template = 'notification_for_candidates_of_new_proposal'
        context = {'proposal': self}
        area = Area.objects.get(id=self.area.id)
        for election in area.elections.all():
            for candidate in election.candidates.all():
                for contact in candidate.contacts.all():
                    context.update({'candidate': candidate})
                    send_mail(context,
                              template,
                              to=[contact.mail])


class ProposalLike(models.Model):
    user = models.ForeignKey(User, related_name="likes")
    proposal = models.ForeignKey(PopularProposal)
    message = models.TextField(null=True, blank=True, help_text=_(u"Quieres decirle algo?"))
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super(ProposalLike, self).save(*args, **kwargs)
        created = self.pk is not None
        if created:
            if self.user.profile.is_organization:
                template = 'new_sponsorshipnotification_to_proposer'
                context = {'like': self}
                send_mail(context,
                          template,
                          to=[self.proposal.proposer.email])
                template = 'new_sponsorshipnotification_to_sponsorer'
                context = {'like': self}
                send_mail(context,
                          template,
                          to=[self.user.email])
            self.numerical_notification()

    def numerical_notification(self):
        the_number = ProposalLike.objects.filter(proposal=self.proposal).count()
        if the_number in settings.WHEN_TO_NOTIFY:
            from popular_proposal.subscriptions import YouAreAHeroNotification, ManyCitizensSupportingNotification
            notifier = YouAreAHeroNotification(proposal=self.proposal,
                                               number=the_number)
            notifier.notify()
            notifier = ManyCitizensSupportingNotification(proposal=self.proposal,
                                                          number=the_number)
            notifier.notify()

    def __str__(self):
        return u'{} apoya {}'.format(self.user.username, self.proposal.title)

    class Meta:
            verbose_name = _(u'Apoyo')
            verbose_name_plural = _(u'Apoyos')


class Commitment(models.Model):
    proposal = models.ForeignKey(PopularProposal,
                                 related_name='commitments')
    candidate = models.ForeignKey(Candidate,
                                  related_name='commitments')
    detail = models.CharField(max_length=12288,
                              null=True,
                              blank=True)
    commited = models.NullBooleanField(default=None)

    def save(self, *args, **kwargs):
        instance = super(Commitment, self).save(*args, **kwargs)
        from popular_proposal.subscriptions import notification_trigger
        notification_trigger('new-commitment',
                             proposal=self.proposal,
                             commitment=self)
        return instance

    def get_absolute_url(self):
        url = reverse('popular_proposals:commitment', kwargs={'candidate_slug': self.candidate.id,
                                                              'proposal_slug': self.proposal.slug})
        return url
