from rest_framework import serializers
from django.utils.text import slugify
from user.models import User
from store.models import Store


class GoogleLoginSerializer(serializers.Serializer):
    """
    Serializer for validating the Google ID token sent from the frontend.
    """
    id_token = serializers.CharField(required=True, write_only=True)


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password',
                  'password_confirm', 'first_name', 'last_name']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        validated_data['username'] = validated_data['email']
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class StoreRegisterSerializer(serializers.Serializer):
    """
    Serializer for store registration - creates both User and Store.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    store_name = serializers.CharField(max_length=255)
    first_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    last_name = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_store_name(self, value):
        # Generate slug and check uniqueness
        slug = slugify(value)
        if Store.objects.filter(slug=slug).exists():
            raise serializers.ValidationError("A store with this name already exists.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        store_name = validated_data['store_name']
        first_name = validated_data.get('first_name', '')
        last_name = validated_data.get('last_name', '')

        # Create user with account_type=STORE
        user = User(
            email=email,
            username=email,
            account_type=User.AccountType.STORE,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(password)
        user.save()

        # Create store
        store = Store.objects.create(
            owner=user,
            name=store_name,
            slug=slugify(store_name),
        )

        return user
