"""Forms for the ``user_tags`` app."""
from django import forms
from django.contrib.contenttypes.models import ContentType

from user_tags.models import DummyModel, UserTagGroup, UserTag, TaggedItem


class UserTagsFormMixin(object):
    """
    Adds all fields declared in the model's TAG_FIELDS attribute to the form.

    """
    def __init__(self, *args, **kwargs):
        """
        If the model has a ``TAG_FIELDS`` attribute, this constructor adds
        a form field to the form for each tag field.

        """
        super(UserTagsFormMixin, self).__init__(*args, **kwargs)

        instance = kwargs.get('instance')
        for tag_field, tag_label in self.Meta.model.TAG_FIELDS:
            self.fields[tag_field] = forms.CharField(
                required=False,
                max_length=4000,
                label=tag_label,
            )

            if not instance:
                continue

            try:
                tagged_item = TaggedItem.objects.get(
                    content_type=ContentType.objects.get_for_model(instance),
                    object_id=instance.pk)
            except TaggedItem.DoesNotExist:
                continue

            user_tags = tagged_item.user_tags.filter(
                user_tag_group__name=tag_field)
            self.initial[tag_field] = ', '.join(
                [tag.text for tag in user_tags])

    def save(self, *args, **kwargs):
        """Saves all tags for this instance."""
        instance = super(UserTagsFormMixin, self).save(*args, **kwargs)

        tagged_item_user = None
        if hasattr(self, 'user'):
            tagged_item_user = self.user
        elif hasattr(instance, 'user'):
            tagged_item_user = instance.user
        elif hasattr(self, 'get_user'):
            tagged_item_user = self.get_user()
        else:
            raise Exception(
                'Could not find a user at self.user and instance.user.'
                ' Please provide a method self.get_user() on your form that'
                " Returns the user who owns the saved instance and it's tags.")

        tagged_items = TaggedItem.objects.filter(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.id)
        tagged_items.delete()
        tagged_item = TaggedItem(content_object=instance)
        tagged_item.save()
        for tag_field, tag_label in self.Meta.model.TAG_FIELDS:
            self.save_tags(tagged_item_user, tagged_item, tag_field,
                self.cleaned_data[tag_field])
        return instance

    def save_tags(self, user, tagged_item, tag_field, tag_data):
        try:
            group = UserTagGroup.objects.get(name=tag_field)
        except UserTagGroup.DoesNotExist:
            group = UserTagGroup(user=user, name=tag_field)
            group.save()
        tags = self.split_tags(tag_data)
        for tag in tags:
            try:
                user_tag = UserTag.objects.get(user_tag_group=group, text=tag)
            except UserTag.DoesNotExist:
                user_tag = UserTag(user_tag_group=group, text=tag)
                user_tag.save()
            tagged_item.user_tags.add(user_tag)

    @staticmethod
    def split_tags(tag_data):
        tags = []
        for tag in tag_data.split(','):
            tag = tag.strip()
            if tag and not tag in tags:
                tags.append(tag)
        return tags


class DummyModelForm(UserTagsFormMixin, forms.ModelForm):
    """We need this to test the ``UserTagsFormMixin``."""
    class Meta:
        model = DummyModel

    def __init__(self, user=None, *args, **kwargs):
        if user is not None:
            self.user = user
        super(DummyModelForm, self).__init__(*args, **kwargs)
