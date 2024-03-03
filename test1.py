
from workflow_tracker_code import WorkflowTracker, BaseTrackerModel, WorkflowTrackerModel
from workflow_states_code  import WorkflowEnum
from pydantic_models import GDriveInput


def valid_mp3_gdrive_input():
    return GDriveInput(gdrive_id='1ukjAXeITUyJ606Y62mho3XOMnsq-tfu5')

WorkflowTracker.update(
status=WorkflowEnum.START.name,
comment= 'adding a comment',
)
print(f"\n----\nWorkflowTrackerModel: {WorkflowTracker.get_model()}")
base_tracker_instance = BaseTrackerModel(transcript_audio_quality="medium",transcript_compute_type="float16",input_mp3=valid_mp3_gdrive_input())
print(f"\n----\nbase_tracker_instance: {base_tracker_instance}")
mod_wftm = WorkflowTrackerModel(status=WorkflowEnum.START.name,comment= 'adding a comment')
print(f"\n----\nmod_wftm: {mod_wftm}")
mod_wftm = base_tracker_instance.model_copy()
print(f"\n----\nmod_wftm: {mod_wftm}")
print(mod_wftm)


# class FooBarModel(BaseModel):
#     banana: float
#     foo: str
#     bar: BarModel


# m = FooBarModel(banana=3.14, foo='hello', bar={'whatever': 123})
# v = m.model_copy(update={'banana': 0})
# print(m.model_copy(update={'banana': 0}))
# #> banana=0 foo='hello' bar=BarModel(whatever=123)
# print(id(m.bar) == id(m.model_copy().bar))
# #> True
# # normal copy gives the same object reference for bar
# print(id(m.bar) == id(m.model_copy(deep=True).bar))
# #> False
# # deep copy gives a new object reference for `bar`
