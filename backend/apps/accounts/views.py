from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import ProfileSerializer, RegistrationSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = (permissions.AllowAny,)


class LoginView(TokenObtainPairView):
    permission_classes = (permissions.AllowAny,)


class RefreshView(TokenRefreshView):
    permission_classes = (permissions.AllowAny,)


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
