import jwt
import datetime
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from customers.models import Customer
from customers.serializers import CustomerRegisterSerializer


@api_view(['POST'])
def register(request):
    """Register a new customer"""
    serializer = CustomerRegisterSerializer(data=request.data)
    if serializer.is_valid():
        customer = serializer.save()
        # Auto-login after register
        payload = {
            'user_id': customer.id,
            'username': customer.username,
            'user_type': 'customer',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT_EXPIRATION_HOURS),
            'iat': datetime.datetime.utcnow(),
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
        return Response({
            "token": token,
            "user": {
                "id": customer.id,
                "username": customer.username,
                "full_name": customer.full_name,
            }
        }, status=status.HTTP_201_CREATED)

    return Response({"error": "Validation failed", "detail": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login(request):
    """Customer login — returns JWT token"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({"error": "Username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = Customer.objects.get(username=username)
    except Customer.DoesNotExist:
        return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)

    if not customer.check_password(password):
        return Response({"error": "Invalid username or password"}, status=status.HTTP_401_UNAUTHORIZED)

    payload = {
        'user_id': customer.id,
        'username': customer.username,
        'user_type': 'customer',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

    return Response({
        "token": token,
        "user": {
            "id": customer.id,
            "username": customer.username,
            "full_name": customer.full_name,
        }
    })


@api_view(['POST'])
def verify_token(request):
    """Verify JWT token — called by API Gateway"""
    token = request.data.get('token')
    if not token:
        return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return Response({
            "valid": True,
            "user_id": payload.get('user_id'),
            "username": payload.get('username'),
            "user_type": payload.get('user_type'),
        })
    except jwt.ExpiredSignatureError:
        return Response({"valid": False, "error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        return Response({"valid": False, "error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
