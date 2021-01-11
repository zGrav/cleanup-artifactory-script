import os
import requests

from sys import exit
from datetime import timezone, datetime

ARTIFACTORY_DAY_LIMIT = int(os.getenv("ARTIFACTORY_DAY_LIMIT", 2))

ARTIFACTORY_API_KEY = os.getenv("ARTIFACTORY_API_KEY", None)
ARTIFACTORY_URL = os.getenv("ARTIFACTORY_URL", "REDACTED")
ARTIFACTORY_DOCKER_REPO = os.getenv("ARTIFACTORY_DOCKER_REPO", "docker-registry")
ARTIFACTORY_DOCKER_IMAGES = os.getenv("ARTIFACTORY_DOCKER_IMAGES", None)

if ARTIFACTORY_API_KEY == None:
    print("MISSING ARTIFACTORY_API_KEY!")
    exit(1)

if ARTIFACTORY_DOCKER_IMAGES == None:
    print("MISSING ARTIFACTORY_DOCKER_IMAGES!")
    exit(1)

ARTIFACTORY_API_URL = '{}/api/search/aql'.format(ARTIFACTORY_URL)
print("Artifactory API Search AQL URL: {}".format(ARTIFACTORY_API_URL))

SPLIT_ARTIFACTORY_DOCKER_IMAGES = ARTIFACTORY_DOCKER_IMAGES.split(',')

for DOCKER_IMAGE in SPLIT_ARTIFACTORY_DOCKER_IMAGES:
    DOCKER_IMAGES_API_PAYLOAD = 'items.find({"repo":{"$eq":"%s"}, "path":{"$match":"%s"}})' % (ARTIFACTORY_DOCKER_REPO, DOCKER_IMAGE)
    print()
    print("{} items lookup query: {}".format(DOCKER_IMAGE, DOCKER_IMAGES_API_PAYLOAD))
    print()

    DOCKER_IMAGES_API_HEADERS = {'content-type': 'text/plain', 'Accept-Charset': 'UTF-8', 'X-JFrog-Art-Api': ARTIFACTORY_API_KEY}
    DOCKER_IMAGES_API_REQUEST = requests.post(ARTIFACTORY_API_URL, data=DOCKER_IMAGES_API_PAYLOAD, headers=DOCKER_IMAGES_API_HEADERS)
    print(DOCKER_IMAGES_API_REQUEST)
    DOCKER_IMAGES_API_RESULT = DOCKER_IMAGES_API_REQUEST.json()["results"]
    print("DONE!")

    DOCKER_IMAGE_INFO = []
    oldPath = ""
    for result in DOCKER_IMAGES_API_RESULT:
        if "_uploads" in result['path']:
            continue
        if oldPath == result['path']:
            continue
        DOCKER_IMAGE_API_URL = '{}/api/storage/{}/{}/manifest.json?properties'.format(ARTIFACTORY_URL, ARTIFACTORY_DOCKER_REPO, result['path'])
        print()
        print("Looking up specific docker info for: {} on API URL: {}".format(result['path'], DOCKER_IMAGE_API_URL))
        print()
        DOCKER_IMAGE_API_HEADERS = {'content-type': 'text/plain', 'Accept-Charset': 'UTF-8', 'X-JFrog-Art-Api': ARTIFACTORY_API_KEY}
        DOCKER_IMAGE_API_REQUEST = requests.get(DOCKER_IMAGE_API_URL, headers=DOCKER_IMAGE_API_HEADERS)
        print(DOCKER_IMAGE_API_REQUEST)
        print()
        DOCKER_IMAGE_API_RESULT = DOCKER_IMAGE_API_REQUEST.json()
        DOCKER_IMAGE_INFO.append(DOCKER_IMAGE_API_RESULT)
        oldPath = result['path']
        print("DONE!")

    print("Cleanup section starting now")
    print()

    LATEST_DOCKER_SHA = next((x["properties"]["sha256"][0] for x in DOCKER_IMAGE_INFO if x["properties"]['docker.manifest'][0] == "latest"), None)

    if LATEST_DOCKER_SHA == None:
        print("LATEST_DOCKER_SHA NOT FOUND!")
        exit(1)
    else:
        print("LATEST_DOCKER_SHA: {}".format(LATEST_DOCKER_SHA))

    DOCKER_IMAGE_INFO[:] = [x for x in DOCKER_IMAGE_INFO if not x["properties"]["sha256"][0] == LATEST_DOCKER_SHA]

    if (len(DOCKER_IMAGE_INFO) == 0):
        print("No cleanup to do on {} Docker Images".format(DOCKER_IMAGE))
        print()
    else:
        print("Going to clean up {} Docker Images".format(DOCKER_IMAGE))
        print()
        for item in DOCKER_IMAGE_INFO:
            formattedUrl = str(item['uri']).rsplit('/', 1)[0].replace('/api/storage', '')
        
            dockerBuildTimestamp = int(item["properties"]['build.timestamp'][0])
            buildDateUtc = datetime.utcfromtimestamp(dockerBuildTimestamp / 1000)
            currentDateUtc = datetime.utcfromtimestamp(datetime.now(tz=timezone.utc).timestamp())
            dateDiff = currentDateUtc - buildDateUtc

            if (dateDiff.days < ARTIFACTORY_DAY_LIMIT):
                print("Build not older than {} days, skipping. Days of build: {}".format(ARTIFACTORY_DAY_LIMIT, dateDiff.days))
                continue
            if (dateDiff.days >= ARTIFACTORY_DAY_LIMIT):
                print("Build is over {} day limit, deletin'. Days of build: {}".format(ARTIFACTORY_DAY_LIMIT, dateDiff.days))
                print("Cleaning up {}".format(formattedUrl))
                print()
                DELETE_ITEM_API_URL = formattedUrl
                DELETE_ITEM_API_HEADERS = {'Accept-Charset': 'UTF-8', 'X-JFrog-Art-Api': ARTIFACTORY_API_KEY}
                DELETE_ITEM_API_REQUEST = requests.delete(DELETE_ITEM_API_URL, headers=DELETE_ITEM_API_HEADERS)
                print(DELETE_ITEM_API_REQUEST)
                print()
    print("DONE!")
    print()

print("Script complete, exiting")
exit(0)
