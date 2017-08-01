from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.http import is_safe_url
from django.shortcuts import resolve_url, redirect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from stats.models import LoginStats

# Avoid shadowing the login() and logout() views below.
from django.contrib.auth import (REDIRECT_FIELD_NAME, login as auth_login, logout as auth_logout)
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.sites.shortcuts import get_current_site

from forms import UsernameLoginForm, CodeForm, CreatePasswordForm

@sensitive_post_parameters()
@csrf_protect
@never_cache

# TODO: TO DELETE
# def root_redirection(request):
#     """
#     Whenever a user tries to access the main page, this view will look at its status and redirect him
#     to the corresponding page.
#     :param request:
#     :return:
#     """
#     redirect_to = request.POST.get("next", request.GET.get("next", ''))
#
#     if redirect_to:
#         return HttpResponseRedirect(redirect_to)
#
#     if request.user.is_superuser:
#         return HttpResponseRedirect("/admin/")
#
#     if hasattr(request.user, "professor"):
#         return HttpResponseRedirect(reverse("professor:dashboard"))
#
#     if hasattr(request.user, "student"):
#         return HttpResponseRedirect(reverse("student_dashboard"))
#
#     return HttpResponseRedirect(reverse("login"))

def username(request, template_name='registration/login_username.haml',
             redirect_field_name=REDIRECT_FIELD_NAME,
             usernamelogin_form=UsernameLoginForm,
             current_app=None, extra_context=None) :
    """
    Displays the username form and handles the login action.
    """

    if request.user.is_superuser:
        return HttpResponseRedirect("/admin/")

    if hasattr(request.user, "professor"):
        return HttpResponseRedirect(reverse("professor:dashboard"))

    if hasattr(request.user, "student"):
        return HttpResponseRedirect(reverse("student_dashboard"))


    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))
    if request.method == "POST":
        form = usernamelogin_form(request.POST)
        if form.is_valid():
            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            user = form.cleaned_data['username']
            return is_pending(request,user)
    else:
        form = usernamelogin_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }

    return TemplateResponse(request, template_name, context,
                        current_app)

def is_pending(request, user):
    """
    Redirect the user either to :
    - code page if he needs to create a password (by giving his code first)
    - password page if he already has a password
    """

    if (user[0].is_pending):
        request.session['user'] = user[1]
        return HttpResponseRedirect(reverse('code_login'))
    else:
        request.session['user'] = user[1]
        return HttpResponseRedirect(reverse('password_login'))

def password(request, template_name='registration/login_password.haml',
             redirect_field_name=REDIRECT_FIELD_NAME,
             authentication_form=AuthenticationForm,
             current_app=None, extra_context=None) :

    """
    Displays the password form and handles the login action.
    """

    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Security check is complete. Log the user in.
            auth_login(request, form.get_user())

            if request.user.is_superuser:
                LoginStats.objects.create(user=request.user, user_kind="admin")
                return HttpResponseRedirect("/admin/")
            elif hasattr(request.user, "professor"):
                LoginStats.objects.create(user=request.user, user_kind="professor")
                return HttpResponseRedirect(reverse("professor:dashboard"))
            elif hasattr(request.user, "student"):
                LoginStats.objects.create(user=request.user, user_kind="student")
                return HttpResponseRedirect(reverse("student_dashboard"))
            else:
                raise Exception("Unknown user kind, can't login")
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'user': request.session['user'],
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app)

def code(request, template_name='registration/login_code.haml',
             redirect_field_name=REDIRECT_FIELD_NAME,
             code_form=CodeForm,
             current_app=None, extra_context=None) :

    """
    Displays the code form and handles the login action.
    """

    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = code_form(request.POST)
        if form.is_valid():
            # Once the code has been verified in the form, allow the user to create its password.
            return HttpResponseRedirect(reverse('create_password'))

    else:
        form = code_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'user': request.session['user'],
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app)

def create_password(request, template_name='registration/create_password.haml',
                    redirect_field_name=REDIRECT_FIELD_NAME,
                    cp_form=CreatePasswordForm,current_app=None, extra_context=None):

    """
    Displays the creation of password form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))
    if request.method == "POST":
        form = cp_form(request.POST)
        if form.is_valid():
            # Once the code has been verified in the form, allow the user to create its password.
            prof_or_stud = form.cleaned_data['username'][0]
            user = prof_or_stud.user
            user.set_password(form.cleaned_data['password'])
            user.save()
            prof_or_stud.is_pending = False
            prof_or_stud.save()
            auth_login(request, user)
            return HttpResponseRedirect(reverse('username_login'))
    else:
        form = cp_form(request)


    current_site = get_current_site(request)
    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'user': request.session['user'],
    }
    return TemplateResponse(request, template_name, context, current_app)


def logout(request, next_page=None,
           template_name='registration/logged_out.html',
           redirect_field_name=REDIRECT_FIELD_NAME,
           current_app=None, extra_context=None):
    """
    Logs out the user and displays 'You are logged out' message.
    """
    auth_logout(request)
    return HttpResponseRedirect(reverse("home"))


def login(request, template_name='registration/login.haml',
          redirect_field_name=REDIRECT_FIELD_NAME,
          authentication_form=AuthenticationForm,
          current_app=None, extra_context=None):
    """
    Displays the login form and handles the login action.
    """
    redirect_to = request.POST.get(redirect_field_name,
                                   request.GET.get(redirect_field_name, ''))

    if request.method == "POST":
        form = authentication_form(request, data=request.POST)
        if form.is_valid():

            # Ensure the user-originating redirection url is safe.
            if not is_safe_url(url=redirect_to, host=request.get_host()):
                redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

            # Security check is complete. Log the user in.
            auth_login(request, form.get_user())

            if request.user.is_superuser:
                user_kind = "admin"
            elif hasattr(request.user, "professor"):
                user_kind = "professor"
            elif hasattr(request.user, "student"):
                user_kind = "student"
            else:
                raise Exception("Unknown user kind, can't login")

            LoginStats.objects.create(user=request.user, user_kind=user_kind)
            return HttpResponseRedirect(redirect_to)
    else:
        form = authentication_form(request)

    current_site = get_current_site(request)

    context = {
        'form': form,
        redirect_field_name: redirect_to,
        'site': current_site,
        'site_name': current_site.name,
    }
    if extra_context is not None:
        context.update(extra_context)
    return TemplateResponse(request, template_name, context,
                            current_app)