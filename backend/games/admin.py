from django.contrib import admin

from .models import Developer, Game, GameComment, GameCommentReaction, GameTag, Genre, PlayerSnapshot, Publisher, RelatedProduct, Tag

admin.site.register(Game)
admin.site.register(Genre)
admin.site.register(Tag)
admin.site.register(GameTag)
admin.site.register(Developer)
admin.site.register(Publisher)
admin.site.register(RelatedProduct)
admin.site.register(PlayerSnapshot)
admin.site.register(GameComment)
admin.site.register(GameCommentReaction)

