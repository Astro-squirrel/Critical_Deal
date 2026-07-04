from rest_framework.response import Response


def ok(data=None, message="ok", status=200):
    return Response({"success": True, "message": message, "data": data}, status=status)


def fail(message, status=400, details=None):
    return Response({"success": False, "message": message, "details": details or {}}, status=status)

