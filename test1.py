from gdrive_helper_code import GDriveHelper
import asyncio

async def test_fetch(gh):
    transcription_status_dict = await gh.fetch_transcription_status_dict('1WtVgEH_Cjf1YNdqjtvNf5SujeOYhjcM1')
    print(transcription_status_dict)

async def main():
    gh = GDriveHelper()
    await test_fetch(gh)

if __name__ == "__main__":
    asyncio.run(main())


