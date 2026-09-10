from django.urls import path

from .views import (
    EvaluationReportView,
    PipelineReportView,
    ProductionReportView,
    RevenueReportView,
)

urlpatterns = [
    path("pipeline/", PipelineReportView.as_view(), name="report-pipeline"),
    path("evaluation/", EvaluationReportView.as_view(), name="report-evaluation"),
    path("revenue/", RevenueReportView.as_view(), name="report-revenue"),
    path("production/", ProductionReportView.as_view(), name="report-production"),
]
