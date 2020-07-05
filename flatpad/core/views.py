import configparser
import json
import netifaces
import os
import subprocess

from bs4 import BeautifulSoup
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from fritzhome.fritz import FritzBox
from netaddr import IPAddress

from core.models import Anonymous, LastCheck, Pad, Presence


def index(request):
    context = {}

    with open(os.path.join(settings.BASE_DIR, "devices.json")) as f:
        devices = json.load(f)
    context["names"] = [list(person.keys())[0] for person in devices["People"]]

    pad = Pad.objects.get_or_create(id=0)[0]
    context["pad_content"] = pad.content
    context["pad_version"] = pad.version

    return render(request, "index.html", context)


@csrf_exempt
def submit_pad(request):
    version = request.POST.get("version")
    content = request.POST.get("content")
    if not version or content is None:
        return HttpResponseBadRequest("No version or content supplied")
    version = int(version)

    with transaction.atomic():
        pad = Pad.objects.get(id=0)
        current_version = pad.version
        if current_version == version:
            version_valid = True
            pad.version += 1
            pad.content = content
            pad.save()
        else:
            version_valid = False

    if not version_valid:
        return HttpResponseBadRequest(
            "The content was changed in the meantime, please reload"
        )
    return HttpResponse("Updated Pad")


def get_presence(request, force_update=False):
    with open(os.path.join(settings.BASE_DIR, "devices.json")) as f:
        devices = json.load(f)
    people = devices["People"]
    searched_macs = []
    ignored_macs = []
    for person in people:
        name = list(person.keys())[0]
        macs = person[name]
        if not isinstance(macs, list):
            macs = [macs]
            person[name] = macs
        person[name] = [mac.upper() for mac in person[name]]
        for mac in person[name]:
            searched_macs.append(mac)
            if not Presence.objects.filter(mac=mac).exists():
                # a mac was added, force an update
                force_update = True
    for mac in devices["Ignored"]:
        ignored_macs.append(mac.upper())

    last_check, created = LastCheck.objects.get_or_create(id=0)
    if created:
        last_check.save()

    if (
        (timezone.now() - last_check.performed).seconds > 60 * 5
        or force_update
        or created
    ):
        present_macs, anonymous_count = search_devices(searched_macs, ignored_macs)

        for mac in searched_macs:
            presence = Presence.objects.get_or_create(mac=mac)[0]
            presence.present = mac in present_macs
            presence.save()

        anonymous = Anonymous.objects.get_or_create(id=0)[0]
        anonymous.count = anonymous_count
        anonymous.save()
        last_check.save()
    else:
        present_macs = []
        for mac in searched_macs:
            if Presence.objects.get(mac=mac).present:
                present_macs.append(mac)
        anonymous_count = Anonymous.objects.get(id=0).count

    presences = []
    for person in people:
        name = list(person.keys())[0]
        present = False
        for mac in person[name]:
            if mac in present_macs:
                present = True
        presences.append((name, present))
    if anonymous_count > 0:
        presences.append((f"+{anonymous_count}", True))
    else:
        presences.append((f"+{anonymous_count}", False))

    return JsonResponse(presences, safe=False)


def update_presence(request):
    return get_presence(request, force_update=True)


def search_devices(searched_macs, ignored_macs):
    try:
        return fritzbox_query(searched_macs, ignored_macs)
    except FritzException:
        return nmap_query(searched_macs, ignored_macs)


class FritzException(Exception):
    pass


def fritzbox_query(searched_macs, ignored_macs):
    config = configparser.ConfigParser()
    config.read(os.path.join(settings.BASE_DIR, "config.ini"))
    ip = config["FritzBox"]["ip"]
    password = config["FritzBox"]["password"]
    if not ip or not password:
        raise FritzException("ip or password not specified")

    box = FritzBox(ip, None, password)
    try:
        box.login()
    except Exception:
        raise FritzException("Login failed")

    r = box.session.get(
        box.base_url + "/net/network_user_devices.lua", params={"sid": box.sid}
    )

    try:
        table = BeautifulSoup(r.text, "lxml").find(id="uiLanActive")
    except AttributeError:
        raise FritzException("Could not extract active devices.")

    rows = table.find_all("tr")

    present_macs = []
    anonymous_count = 0

    for row in rows:
        columns = row.find_all("td")
        if len(columns) >= 4:
            mac = columns[3].text.upper()
            if mac in searched_macs:
                present_macs.append(mac)
            elif mac not in ignored_macs:
                anonymous_count += 1

    return present_macs, anonymous_count


def nmap_query(searched_macs, ignored_macs):
    active_devices = []
    # look through all available interfaces
    for interface in netifaces.interfaces():
        if (
            interface == "lo"  # loopback
            or interface.startswith("virbr")  # libvirt
            or interface.startswith("lxcbr")  # lxc
            or interface.startswith("docker")  # docker
            or interface.startswith("br-")  # bridges
            or interface.startswith("veth")  # virtual devices
        ):
            continue
        # get the first set of IPv4 addresses (there will probably be only one)
        try:
            addresses = netifaces.ifaddresses(interface)[netifaces.AF_INET][0]
        except KeyError:
            # the interface has no IPv4 addresses
            continue
        # check if the interface received an address (= is connected)
        if "addr" in addresses:
            ip = addresses["addr"]
            netmask = addresses["netmask"]
            suffix = IPAddress(netmask).netmask_bits()
            output = subprocess.check_output(
                ["/usr/bin/nmap", "--privileged", "-sn", f"{ip}/{suffix}"],
                universal_newlines=True,
            )
            for line in output.split("\n"):
                if line.startswith("MAC Address:"):
                    mac_address = line.split()[2]
                    active_devices.append(mac_address.upper())

    present_macs = []
    anonymous_count = 0

    for mac in active_devices:
        if mac in searched_macs:
            present_macs.append(mac)
        elif mac not in ignored_macs:
            anonymous_count += 1

    return present_macs, anonymous_count
