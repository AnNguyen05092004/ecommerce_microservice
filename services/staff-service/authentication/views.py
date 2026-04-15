import jwt
import datetime
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from staff.models import Staff


@api_view(['POST'])
def login(request):
    """Staff/Admin login — returns JWT token"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response(
            {"error": "Username and password are required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        staff = Staff.objects.get(username=username)
    except Staff.DoesNotExist:
        return Response(
            {"error": "Invalid username or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not staff.is_active:
        return Response(
            {"error": "Account is deactivated"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not staff.check_password(password):
        return Response(
            {"error": "Invalid username or password"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    # Generate JWT token
    payload = {
        'user_id': staff.id,
        'username': staff.username,
        'role': staff.role,
        'user_type': 'staff',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        'iat': datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

    return Response({
        "token": token,
        "user": {
            "id": staff.id,
            "username": staff.username,
            "full_name": staff.full_name,
            "role": staff.role,
        }
    })


@api_view(['POST'])
def verify_token(request):
    """Verify JWT token — called by API Gateway"""
    token = request.data.get('token')

    if not token:
        return Response(
            {"error": "Token is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])

        # Check user still exists and is active
        if payload.get('user_type') == 'staff':
            try:
                staff = Staff.objects.get(id=payload['user_id'])
                if not staff.is_active:
                    return Response(
                        {"valid": False, "error": "Account deactivated"},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except Staff.DoesNotExist:
                return Response(
                    {"valid": False, "error": "User not found"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        return Response({
            "valid": True,
            "user_id": payload.get('user_id'),
            "username": payload.get('username'),
            "role": payload.get('role'),
            "user_type": payload.get('user_type'),
        })

    except jwt.ExpiredSignatureError:
        return Response(
            {"valid": False, "error": "Token expired"},
            status=status.HTTP_401_UNAUTHORIZED
        )
    except jwt.InvalidTokenError:
        return Response(
            {"valid": False, "error": "Invalid token"},
            status=status.HTTP_401_UNAUTHORIZED
        )
