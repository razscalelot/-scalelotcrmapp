from rest_framework import serializers
from pymongo import MongoClient
from decouple import config

primary = MongoClient(config('MONGO_CONNECTION_STRING')).scalelotcrmapp


class SuperAdminSerializer(serializers.Serializer):
    class Meta:
        model = primary.list_collection_names(filter={'name': 'customers'})
        fields = "__all__"
