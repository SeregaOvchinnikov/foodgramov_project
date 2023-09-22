# isort:skip_file
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from recipes.models import (
    Ingredient,
    IngredientAmount,
    Recipe,
    Tag
)
from users.models import User

from ..filters import IngredientSearchFilter, RecipeFilter
from ..permissions import AuthorOrReadOnly
from ..serializers.recipes import (
    FavoriteSerializer,
    IngredientSerializer,
    RecipeGETSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    ShoppingCartSerializer,
    TagSerializer
)
from ..utils import create_shopping_cart


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для создания обьектов класса Tag."""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для создания обьектов класса Ingredient."""
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientSearchFilter
    search_fields = ('^name', )


class RecipeViewSet(viewsets.ModelViewSet):
    """Вьюсет для создания обьектов класса Recipe."""
    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly, AuthorOrReadOnly
    )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    http_method_names = ['get', 'post', 'patch', 'delete']

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        url_name='favorite',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def manage_favorite(self, request, pk):
        """Позволяет текущему пользователю добавлять или
        удалять рецепты из избранного.
        """
        return self.create_or_delete_object(
            request, pk, FavoriteSerializer, RecipeShortSerializer
        )

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='shopping_cart',
        url_name='shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def manage_shopping_cart(self, request, pk):
        """Позволяет текущему пользователю добавлять или
        удалять рецепты из списка покупок.
        """
        return self.create_or_delete_object(
            request, pk, ShoppingCartSerializer, RecipeShortSerializer
        )

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        """Позволяет текущему пользователю загрузить список покупок."""
        ingredients_cart = (
            IngredientAmount.objects.filter(
                recipe__shopping_cart__user=request.user
            ).values(
                'ingredient__name',
                'ingredient__measurement_unit',
            ).order_by(
                'ingredient__name'
            ).annotate(ingredient_value=Sum('amount'))
        )
        return create_shopping_cart(ingredients_cart)

    def get_serializer_class(self):
        """Определяет какой сериализатор будет использоваться
        для разных типов запроса.
        """
        if self.request.method == 'GET':
            return RecipeGETSerializer
        return RecipeSerializer

    def create_or_delete_object(
        self, request, pk, serializer_class, response_serializer_class
    ):
        """Обобщенная функция для создания или удаления
        объектов (избранное, корзина).
        """
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            serializer = serializer_class(
                data={'user': request.user.id, 'recipe': recipe.id}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            serializer_response = response_serializer_class(recipe)
            return Response(
                serializer_response.data, status=status.HTTP_201_CREATED
            )

        favorite_recipe = get_object_or_404(
            serializer_class.Meta.model, user=request.user, recipe=recipe
        )
        favorite_recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['get'],
        url_path='author_recipes',
        url_name='author_recipes',
        permission_classes=(permissions.IsAuthenticated,)
    )
    def author_recipes(self, request, pk):
        """Позволяет получить рецепты автора по его ID."""
        author = get_object_or_404(User, pk=pk)
        recipes = Recipe.objects.filter(author=author)
        serializer = RecipeShortSerializer(recipes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
