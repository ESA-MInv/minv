# ------------------------------------------------------------------------------
#
# Project: Master Inventory <http://github.com/ESA-MInv/minv>
# Authors: Fabian Schindler <fabian.schindler@eox.at>
#
# ------------------------------------------------------------------------------
# Copyright (C) 2016 European Space Agency
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies of this Software or works derived from this Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ------------------------------------------------------------------------------


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from minv.inventory import models


def login_view(request):
    """ Django view to log in as a user. Logs out when the user was logged in
    before.
    """
    logout(request)
    username = password = ''
    login_error = None
    if request.POST:
        username = request.POST['username']
        password = request.POST['password']
        next_ = request.POST.get('next')

        user = authenticate(username=username, password=password)
        if user is not None and user.is_active:
            login(request, user)
            if next_:
                return redirect(next_)
            return redirect('root')
        else:
            login_error = True
    return render(
        request, 'minv/login.html', {
            "next": request.GET.get("next"),
            "login_error": login_error
        }
    )


def logout_view(request):
    """ Django view to log out the current user.
    """
    logout(request)
    next_ = request.GET.get("next")
    if next_:
        return redirect(next_)
    return redirect('root')


@login_required(login_url="login")
def root_view(request):
    """ The root view of the Master Inventory.
    """
    return render(
        request, "minv/root.html", {
            "collections": models.Collection.objects.all()
        }
    )
