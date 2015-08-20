from django.db import models


class MissionAndType(models.Model):
    name = models.CharField(max_length=512)
    file_type = models.CharField(max_length=512)

    class Meta:
        unique_together = (("name", "file_type"),)


class Location(models.Model):
    mission = models.ForeignKey("MissionAndType")
    url = models.URLField()
    location_type = models.CharField(max_length=4,
                                     choices=(("oads", "OADS"), ("nga", "ngA")))


class IndexFile(models.Model):
    location = models.ForeignKey("Location")
    filename = models.CharField(max_length=512)
    begin_time = models.DateTimeField()
    end_time = models.DateTimeField()
    update_time = models.DateTimeField()
    insertion_time = models.DateTimeField(auto_now_add=True)


class Record(models.Model):
    location = models.ForeignKey("Location")
    filename = models.CharField(max_length=512)

    index_file = models.ForeignKey("IndexFile")

    # query fields
    # TODO: region = # TODO
    orbit = models.IntegerField(db_index=True)
    track = models.IntegerField(db_index=True)
    frame = models.IntegerField(db_index=True)
    platformSerialIdentifier = models.CharField(max_length=64, db_index=True)
    missionPhase = models.CharField(max_length=64, db_index=True)
    operationalMode = models.CharField(max_length=64, db_index=True)
    swath = models.IntegerField(db_index=True)
    productId = models.CharField(max_length=256, db_index=True)
    # TODO: footprintCentre
    processingCentre = models.CharField(max_length=256, db_index=True)
    processingData = models.DateTimeField(db_index=True)
    processingMode = models.CharField(max_length=64, db_index=True)
    processorVersion = models.CharField(max_length=32, db_index=True)
    acquisitionStation = models.CharField(max_length=256, db_index=True)
    orbitDirection = models.CharField(max_length=4, db_index=True,
                                      choices=(("ASC", "ascending"),
                                               ("DESC", "descending")))
    productQualityDegredatation = models.CharField(max_length=64, db_index=True)
    productQualityStatus = models.CharField(max_length=64, db_index=True)
    productQualityDegredatationTag = models.CharField(max_length=64, db_index=True)

    class Meta:
        unique_together = (("filename", "location"),)


class Annotation(models.Model):
    record = models.ForeignKey("Record")
    text = models.TextField()
    insertion_time = models.DateTimeField(auto_now_add=True)
