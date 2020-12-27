from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_text
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from .tokens import account_activation_token, code_generator
from django.template.loader import render_to_string

from kavenegar import *

from .forms import SignUpForm,SmsActivationForm
from .tokens import account_activation_token
from django.conf import settings 
from django.core.mail import send_mail 
from registration.settings import EMAIL_HOST_USER
import requests


def home_view(request):
    url = 'https://dog.ceo/api/breeds/image/random'
    r = requests.get(url)
    droplets = r.json()
    droplet_list = []
    aks = droplets['message']
    # print('aks ===== ', aks)

    context = { 'aks': aks}
    return render(request,'home.html', context=context)

def activation_sent_view(request):
    return render(request, 'activation_sent.html')

from redis import Redis
from django.conf import settings

r = Redis(db=0)


def sms_activation(request):
    if request.method  == 'POST':
        form = SmsActivationForm(request.POST)
        if form.is_valid():
            activation_code = form.cleaned_data.get('sms_code')
            print("activation_code = ",activation_code)
            
            # retrive from redis and verify
            user_pk = r.lrange(activation_code,0,0)[0].decode('utf-8')
            print("user pk = " ,user_pk)
            user_obj = User.objects.get(pk=user_pk)
            user_obj.is_active = True
            user_obj.save()
            return redirect('home')
    else:
        form = SmsActivationForm()
    return render(request,'sms_activation.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    key_name= 'token'+force_text(urlsafe_base64_decode(uidb64))
    trash, redis_uid,redis_token = r.lrange(key_name,0,2)
    if user is not None and redis_uid.decode('utf-8') == uidb64 and redis_token.decode('utf-8') == token:
        print('successfuly activate')
        user.is_active = True
        user.profile.signup_confirmation = True
        user.save()
        login(request, user)
        print("activated!")
        return redirect('home')
    else:
        return render(request, 'activation_invalid.html')


def signup_view(request):
    if request.method  == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.refresh_from_db()
            user.profile.first_name = form.cleaned_data.get('first_name')
            user.profile.last_name = form.cleaned_data.get('last_name')
            user.profile.email = form.cleaned_data.get('email')
            user.profile.phon_number = form.cleaned_data.get('phon_number')
            print("user.profile.phon_number = ",user.profile.phon_number)
            user.is_active = False
            user.save()

            # sms activation context
            mobile = user.profile.phon_number
            uniq_code = code_generator(mobile)
            time_to_expire_s = 300 # 300 sec
            r.rpush(uniq_code, user.pk)
            r.expire(uniq_code , time_to_expire_s)

            # receptor set to a contant number because of restrictions of free SMS panel!
            # and should replaced by 'mobile'
            api = KavenegarAPI('4C4254557851522F6F64324978657649367A43484E577A7443484470415350464E5761566C2B4F336949733D')
            params = { 'sender' : '10004346', 'receptor': '09372046310', 'message' : uniq_code }
            response = api.sms_send( params)

            # Email acivation context
            current_site = get_current_site(request)
            subject = 'Please Activate Your Account'
            message = render_to_string('activation_request.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            data = [str(user) ,urlsafe_base64_encode(force_bytes(user.pk)) , account_activation_token.make_token(user)]
                        
            for item in data:
                r.rpush("token"+str(user.pk),item)
                r.expire("token"+str(user.pk), time_to_expire_s)
            
            recepient = user.email
            send_mail(subject,message, EMAIL_HOST_USER, [recepient], fail_silently = False)
            return redirect('activation_sent')
    else:
        form = SignUpForm()
    
    return render(request, 'signup.html', {'form': form})