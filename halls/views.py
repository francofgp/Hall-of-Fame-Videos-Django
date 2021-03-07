from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import generic
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login
from .models import Hall, Video
from .forms import VideoForm, SearchForm
from django.http import Http404, JsonResponse
import urllib  # para la api
from django.forms.utils import ErrorList
import requests

# para crear muchos forms a la vez (agregar 5 videos a la vez
# en vez de estar llendo a create 5 veces, lo haces todo
# en la misma pagina)
from django.forms import formset_factory

# mixing para permisos
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

YOUTUBE_API_KEY = 'AIzaSyCuEvJMP4WG-lpRmZBpSF34CLz3OzJUB0Q'


def home(request):
    recent_halls = Hall.objects.all().order_by(
        "-id")[:3]  # obtenemos los ultimos 3
    popular_halls = [Hall.objects.get(pk=5), Hall.objects.get(pk=6)]
    return render(request, "halls/home.html", {"recent_halls": recent_halls, "popular_halls": popular_halls})


@login_required
def dashboard(request):
    halls = Hall.objects.filter(user=request.user)
    return render(request, "halls/dashboard.html", {"halls": halls})


""" 
EJEMPLO DE urllib.parse.quote("ALGO")
>>> import urllib.parse
>>> query = 'Hellö Wörld@Python'
>>> urllib.parse.quote(query)
'Hell%C3%B6%20W%C3%B6rld%40Python'
 """


@login_required
def video_search(request):
    search_form = SearchForm(request.GET)
    if search_form.is_valid():
        encoded_search_term = urllib.parse.quote(
            search_form.cleaned_data["search_term"])
        response = requests.get(
            f'https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults=6&q={encoded_search_term}&key={YOUTUBE_API_KEY}')
        # https://youtube.googleapis.com/youtube/v3/search?part=snippet&maxResults=6&q=batman&key=[YOUR_API_KEY]

        return JsonResponse(response.json())
        # return JsonResponse({"hello": search_form.cleaned_data["search_term"]})
    return JsonResponse({"error": "Not able to validate form"})


@login_required
def add_video(request, pk):
    # por si queremos usar formset habria que hacer algo asi
    # luego un "for" en el if y algo asi, esto es dato random nomas
    #VideoFormSet = formset_factory(VideoForm, extra=5)
    #form = VideoFormSet()

    form = VideoForm()
    search_form = SearchForm()

    # para agarrar el HALL usamos la PK de la URL
    # hacemos una query buscando en los halls la PK que tiene la PK de la url
    hall = Hall.objects.get(pk=pk)
    # correct hall for correct user
    if not hall.user == request.user:
        # si el user del hall y de logeado es diferente
        raise Http404

    if request.method == "POST":
        # create
        form = VideoForm(request.POST)
        if form.is_valid():
            video = Video()
            video.hall = hall
            # asi tenemos la info del form, le pasamos lo que buscamos
            video.url = form.cleaned_data["url"]
            # LIBRERIA PARA PARSE URL
            parsed_url = urllib.parse.urlparse(video.url)

            # si el video es
            # https://www.youtube.com/watch?v=dorsTn3Lsl4
            # despues de la "v" cortamos,
            # de ahi el get("v") ese es el ID del video
            video_id = urllib.parse.parse_qs(parsed_url.query).get("v")
            # para saber si obtuvimos una ID
            if video_id:
                # cero porque urllib devuelve un lista
                video.youtube_id = video_id[0]
                # lo hacemos con la API a esto ahora
                # video.title = filled_form.cleaned_data["title"]
                # video.youtube_id = filled_form.cleaned_data["youtube_id"]

                # Trabajo con API
                # lo sacamos de aca
                # https://developers.google.com/youtube/v3/docs/videos/list?apix_params=%7B%22part%22%3A%5B%22snippet%22%5D%2C%22id%22%3A%5B%221jky7itg7wk%22%5D%7D&apix=true
                # 'https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id=1jky7itg7wk&key=[YOUR_API_KEY]'
                # hacemos un get a esa API que la sacamos de google el ejemplo de arriba
                # y la tuneamos para pasarlo los parametros a mano
                response = requests.get(
                    f'https://youtube.googleapis.com/youtube/v3/videos?part=snippet&id={video_id[0]}&key={YOUTUBE_API_KEY}')
                # a la respuesta la hacemos JSON porque esta RAW para trabajar mejor
                json = response.json()
                title = json["items"][0]["snippet"]["title"]
                video.title = title
                video.save()

                return redirect("detail_hall", pk)
            else:
                errors = form._errors.setdefault("url", ErrorList())
                errors.append("needs to be a YouTube URL")

    return render(request, "halls/add_video.html", {"form": form,
                                                    "search_form": search_form,
                                                    "hall": hall})


class DeleteVideo(LoginRequiredMixin, generic.DeleteView):
    model = Video
    template_name = "halls/delete_video.html"
    success_url = reverse_lazy("dashboard")

    # para que cuando uno elimine un video sea el creador del mismo
    def get_object(self):  # cuando alguien valla a agarrar un objeto
        # esto agarra el objeto que estamos buscando
        video = super(DeleteVideo, self).get_object()
        if not video.hall.user == self.request.user:
            raise Http404
        return video


class SignUp(generic.CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy("dashboard")
    template_name = "registration/signup.html"

    def form_valid(self, form):
        # para que se registre y se logee al mismo tiempo
        # si todo ta joya hacemos esto
        # super va a devolver un objeto
        view = super(SignUp, self).form_valid(form)
        username, password = form.cleaned_data.get(
            "username"), form.cleaned_data.get("password1")
        user = authenticate(username=username, password=password)
        login(self.request, user)
        return view


class CreateHall(LoginRequiredMixin, generic.CreateView):
    model = Hall
    template_name = "halls/create_hall.html"
    fields = ["title"]
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        # para que le añada el usuario
        form.instance.user = self.request.user
        super(CreateHall, self).form_valid(form)
        # redirijimos a donde queremos
        return redirect("dashboard")


class DetailHall(generic.DetailView):
    model = Hall
    template_name = "halls/detail_hall.html"


class UpdateHall(LoginRequiredMixin, generic.UpdateView):
    model = Hall
    template_name = "halls/update_hall.html"
    fields = ["title"]
    success_url = reverse_lazy("dashboard")

    # para que cuando uno elimine un video sea el creador del mismo
    def get_object(self):  # cuando alguien valla a agarrar un objeto
        # esto agarra el objeto que estamos buscando
        hall = super(UpdateHall, self).get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall


class DeleteHall(LoginRequiredMixin, generic.DeleteView):
    model = Hall
    template_name = "halls/delete_hall.html"
    success_url = reverse_lazy("dashboard")

    # para que cuando uno elimine un video sea el creador del mismo
    def get_object(self):  # cuando alguien valla a agarrar un objeto
        # esto agarra el objeto que estamos buscando
        hall = super(DeleteHall, self).get_object()
        if not hall.user == self.request.user:
            raise Http404
        return hall
