import logging
import os
import traceback
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import ScopedRateThrottle
from .serializers import ProfileSerializer, RegistrationSerializer


logger = logging.getLogger(__name__)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'auth'

    def handle_exception(self, exc):
        if isinstance(exc, APIException):
            return super().handle_exception(exc)

        locations = ' > '.join(
            f'{os.path.basename(frame.filename)}:{frame.lineno}:{frame.name}'
            for frame in traceback.extract_tb(exc.__traceback__)[-6:]
        )
        cause = exc.__cause__
        sqlstate = getattr(cause, 'sqlstate', None) or getattr(cause, 'pgcode', None)
        logger.error(
            'Unhandled registration failure; exception_type=%s sqlstate=%s locations=%s',
            type(exc).__name__,
            sqlstate or 'n/a',
            locations or 'unavailable',
        )
        return Response(
            {'detail': 'Registration could not be completed. Please try again.'},
            status=500,
        )


class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'auth'


class RefreshView(TokenRefreshView):
    permission_classes = (permissions.AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = 'auth'


class LogoutView(APIView):
    def post(self, request):
        token = request.data.get('refresh')
        if not token:
            return Response({'detail': 'Refresh token is required.'}, status=400)
        try:
            refresh_token = RefreshToken(token)
            if str(refresh_token.get('user_id')) != str(request.user.pk):
                return Response({'detail': 'Refresh token does not belong to this user.'}, status=400)
            refresh_token.blacklist()
        except Exception:
            return Response({'detail': 'Invalid refresh token.'}, status=400)
        return Response(status=204)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer

    def get_object(self):
        return self.request.user
