from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTests(TestCase):
    """Test publicly available ingredients API"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test list not view for unlogged users"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTests(TestCase):
    """Test private ingredients API"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'testuser@company.com', 'testpass'
        )
        self.client.force_authenticate(user=self.user)

    def test_ingredients_list_available(self):
        """Test ingredients list is available for authorized user"""
        Ingredient.objects.create(name='Cucumber', user=self.user)
        Ingredient.objects.create(name='Orange', user=self.user)

        ings = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ings, many=True)

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredient_are_limited_to_user(self):
        """Test that ingredients for the authenticated user are returned"""
        no_log_user = get_user_model().objects.create_user(
            'nologuser@company.com', 'nologpass'
        )

        Ingredient.objects.create(name='Sault', user=no_log_user)
        ingredient = Ingredient.objects.create(name='Sugar', user=self.user)

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], ingredient.name)

    def test_create_ingredient_successfull(self):
        """Test create a new ingredient"""
        payload = {'name': 'Cabbage'}

        res = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        exists = Ingredient.objects.filter(
            name=payload['name'],
            user=self.user
        ).exists()

        self.assertTrue(exists)

    def test_create_invalid_ingredient_failed(self):
        """Test creating invalid-named ingredient failed"""
        payload = {'name': ''}
        res = self.client.post(INGREDIENTS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_ingredients_assigned_to_recipes(self):
        """Test retrieving ingredients list assigned to recipes only"""
        ing1 = Ingredient.objects.create(user=self.user, name='Sugar')
        ing2 = Ingredient.objects.create(user=self.user, name='Salt')
        recipe1 = Recipe.objects.create(
            title='Greece salad',
            time_minutes=15,
            price=10.00,
            user=self.user
        )
        recipe1.ingredients.add(ing1)
        recipe2 = Recipe.objects.create(
            title='Summer salad',
            time_minutes=7,
            price=10.00,
            user=self.user
        )
        recipe2.ingredients.add(ing1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        serializer1 = IngredientSerializer(ing1)
        serializer2 = IngredientSerializer(ing2)

        self.assertIn(serializer1.data, res.data)
        self.assertNotIn(serializer2.data, res.data)

    def test_retrieve_assigned_only_ingredients_unique_list(self):
        """Test is retrieving indredients list has unique items"""
        ing = Ingredient.objects.create(user=self.user, name='Potato')
        Ingredient.objects.create(user=self.user, name='Milk')
        recipe1 = Recipe.objects.create(
            title='Roasted potato',
            time_minutes=20,
            price=15.00,
            user=self.user
        )
        recipe1.ingredients.add(ing)
        recipe2 = Recipe.objects.create(
            title='Borsch',
            time_minutes=40,
            price=30.00,
            user=self.user
        )
        recipe2.ingredients.add(ing)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
