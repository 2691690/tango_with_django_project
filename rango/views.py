from datetime import datetime
from multiprocessing import context
from unicodedata import category
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.urls import reverse
from rango.forms import CategoryForm, PageForm
from rango.models import Category
from rango.models import Page
from rango.forms import CategoryForm
from rango.forms import PageForm, UserForm, UserProfileForm
from django.shortcuts import redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required


def index(request):
    # Query the database for a list of ALL categories currently stored.
    # Order the categories by the number of likes in desc order
    # Retrieve the top 5 only -- or all if less than 5
    # Place the list in our context_dict dictionary (with our boldmessage)
    # that will be passed to the template engine
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]

    context_dict = {}
    context_dict['boldmessage'] = 'Crunchy, creamy, cookie, candy, cupcake!'
    context_dict['categories'] = category_list
    context_dict['pages'] = page_list

    visitor_cookie_handler(request)

    response = render(request, 'rango/index.html', context=context_dict)
    return response

def about(request):
    context_dict = {'boldmessage': 'Crunchy, creamy, cookie, candy, cupcake!'}
    if request.session.test_cookie_worked():
        print("TEST COOKIE WORKED!")
        request.session.delete_test_cookie()

    visitor_cookie_handler(request)
    context_dict['visits'] = request.session['visits']

    response = render(request, 'rango/about.html', context=context_dict)
    return response


def show_category(request, category_name_slug):
    context_dict = {}

    try:
        # can we find a category name slug with the given name?
        # if not, the .get() method raises a DoesNotExist exception
        # the .get() method returns one model instance or raises an exception

        category = Category.objects.get(slug=category_name_slug)

        # retrieve all of the associated pages
        # the filter() will return a list of page objects or an empty list.
        pages = Page.objects.filter(category=category)

        # adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # we also add the category object from the database to the context dict
        # we'll use this in the template to verify that the category exists.
        context_dict['category'] = category
    except Category.DoesNotExist:
        # if we didn't find the specd category, do nothing
        context_dict['category'] = None
        context_dict['pages'] = None

    # render the result and return to the client
    return render(request, 'rango/category.html', context=context_dict)

@login_required
def add_category(request):
    form = CategoryForm()

    # a http post??
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            # save the new category to the database
            form.save(commit=True)
            # now the category is saved, we could confirm this
            # for now just redirect the user back to the index view
            return redirect('/rango/')
        else:
            # the supplied form contained errors -
            # just print them to the terminal
            print(form.errors)

        # handle the bad form, new form, no form supplied cases -
        # render the form with any error messages
    return render(request, 'rango/add_category.html', {'form': form})

@login_required
def add_page(request, category_name_slug):
    try:
        category = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
        category = None

    if category is None:
        return redirect('/rango/')

    form = PageForm()

    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            # save the new category to the database
            page = form.save(commit=False)
            page.category = category
            page.views = 0
            page.save()

            return redirect(reverse('rango:show_category',
                                    kwargs={'category_name_slug': category_name_slug}))
        else:
            # the supplied form contained errors -
            # just print them to the terminal
            print(form.errors)

        # handle the bad form, new form, no form supplied cases -
        # render the form with any error messages
    context_dict = {'form': form, 'category': category}
    return render(request, 'rango/add_page.html', context=context_dict)


def register(request):
    # a bool for telling temoplate if registration was successful
    # set to false initially
    registered = False

    # if it's a HTTP POST we're interested in processing form data
    if request.method == 'POST':
        # attempt to grab info from the raw form data
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)

        # if the two forms are valid
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()

            # hash the password and update user obj
            user.set_password(user.password)
            user.save()

            # now sort out the UserProfile instance
            # Since we need to set the user attribute ourselves,
            # we set commit = False. this delays saving the model
            # until we are ready to avoid integrity problems
            profile = profile_form.save(commit=False)
            profile.user = user

            # if the user provided a profile pic, get it from the form
            # and put it in the UserProfile model
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # now save the UserProfile model instance
            profile.save()

            # update to indicate the template registration was good
            registered = True
        else:
            # invalid form or forms
            # print problems to the terminal
            print(user_form.errors, profile_form.errors)
    else:
        # not a HTTP POST, so render the form using two modelform instances
        # these forms will be blank, readu for user input
        user_form = UserForm()
        profile_form = UserProfileForm()

    # render the tempolate depending on context
    return render(request, 'rango/register.html',
                  context={'user_form': user_form,
                           'profile_form': profile_form,
                           'registered': registered})


def user_login(request):

    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
            # This information is obtained from the login form.
            # We use request.POST.get('<variable>') as opposed
            # to request.POST['<variable>'], because the
            # request.POST.get('<variable>') returns None if the
            # value does not exist, while request.POST['<variable>']
            # will raise a KeyError exception.
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                 # We'll send the user back to the homepage.
                login(request, user)
                return redirect(reverse('rango:index'))
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print(f"Invalid login details: {username}, {password}")
            return HttpResponse("Invalid login details supplied.")

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render(request, 'rango/login.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect(reverse('rango:index'))

@login_required
def restricted(request):
    # return HttpResponse("Since you're logged in, you can see this text!")
    return render(request, 'rango/restricted.html')


def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, 'visits', '1'))
    last_visit_cookie = get_server_side_cookie(request, 'last_visit', str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7], '%Y-%m-%d %H:%M:%S')
    
    # If it's been more than a day since the last visit...
    if (datetime.now() - last_visit_time).days > 0:
        visits = visits + 1
        # Update the last visit cookie now that we have updated the count
        request.session['last_visit'] = str(datetime.now())
    else:
        # Set the last visit cookie
        request.session['last_visit'] = last_visit_cookie

    # Update/set the visits cookie
    request.session['visits'] = visits

def get_server_side_cookie(request, cookie, default_val=None):
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val

