"""터미널에서 최신값을 확인한다.  실행: python check_data.py"""
import config
import indicators


def main():
    data = indicators.build(config.get_key("FRED_API_KEY"), config.get_key("ECOS_API_KEY"))
    for i in data.values():
        if i.ok:
            print(f"{i.name:<24} {i.fmt(i.latest):>14}  ({i.latest_date:%Y-%m-%d})  변화 {i.fmt_delta()}")
        else:
            print(f"{i.name:<24} 실패: {i.error}")


if __name__ == "__main__":
    main()
