#!/usr/bin/env sh
#
# 아티팩트가 비어 있는 채로 업로드되는 것을 막는다.
#
# upload-artifact 는 매칭되는 파일이 하나도 없으면 아티팩트 자체를 만들지
# 않는다. 그러면 TestHub 전송 단계가 "Artifact '...' not found" 로 죽고,
# 그 시점 이후의 sub-project 는 전부 보고되지 못한다. 즉 프로젝트 하나의
# 실행 실패가 전체 리포팅을 무너뜨린다.
#
# 그래서 리포트가 없으면 "실행 실패" 를 담은 최소 리포트를 대신 남긴다.
# 통과로 위장하지 않는다 - JUnit 은 failure 로, 커버리지는 0% 로 남겨서
# TestHub 에서 문제가 그대로 드러나게 한다.
#
# usage: ensure-reports.sh <project-name> <test-results-dir> [coverage-dir]
# Empty directories are skipped for selective artifact recovery.

set -eu

PROJECT="$1"
TEST_DIR="$2"
COVERAGE_DIR="${3:-}"

# 디렉터리 안에 내용이 있는 .xml 이 하나라도 있으면 0
has_report() {
    [ -d "$1" ] || return 1
    [ -n "$(find "$1" -name '*.xml' -size +0c 2>/dev/null | head -n 1)" ]
}

if [ -n "$TEST_DIR" ]; then
    mkdir -p "$TEST_DIR"

    if has_report "$TEST_DIR"; then
        echo "test report present in $TEST_DIR"
    else
        echo "::warning::no test report in $TEST_DIR - writing a failure placeholder so TestHub reporting survives"
        FAILURE_DETAILS="${REPORT_FAILURE_CONTEXT:-The test command did not produce a report in $TEST_DIR. The test run itself failed - see the Run tests step log for this job.}"
        XML_DETAILS=$(printf '%s' "$FAILURE_DETAILS" | sed 's/\&/\&amp;/g; s/</\</g; s/>/\>/g')
        cat > "$TEST_DIR/result.xml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="$PROJECT" tests="1" failures="1" errors="0" time="0">
  <testsuite name="$PROJECT" tests="1" failures="1" errors="0" time="0">
    <testcase classname="$PROJECT" name="test-run-produced-a-report" time="0">
      <failure message="no test report was produced">$XML_DETAILS</failure>
    </testcase>
  </testsuite>
</testsuites>
EOF
    fi
fi

[ -n "$COVERAGE_DIR" ] || exit 0

mkdir -p "$COVERAGE_DIR"

if has_report "$COVERAGE_DIR"; then
    echo "coverage report present in $COVERAGE_DIR"
else
    echo "::warning::no coverage report in $COVERAGE_DIR - writing an empty (0%) cobertura report with placeholder structure"
    cat > "$COVERAGE_DIR/coverage.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<coverage line-rate="0" branch-rate="0" lines-covered="0" lines-valid="1" branches-covered="0" branches-valid="0" complexity="0" version="1" timestamp="0">
  <sources>
    <source>.</source>
  </sources>
  <packages>
    <package name="placeholder" line-rate="0" branch-rate="0" complexity="0">
      <classes>
        <class name="placeholder" filename="placeholder.py" line-rate="0" branch-rate="0" complexity="0">
          <methods/>
          <lines>
            <line number="1" hits="0" branch="false"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
EOF
fi
