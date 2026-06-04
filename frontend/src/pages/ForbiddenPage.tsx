import { Link } from "react-router-dom";

import { UI_TEXT, resolveStoredLocale } from "../locales";

export default function ForbiddenPage() {
  const ui = UI_TEXT[resolveStoredLocale()];

  return (
    <main className="screen-center stack-gap">
      <p className="eyebrow">403</p>
      <h1>{ui.forbiddenTitle}</h1>
      <Link className="secondary-button" to="/">
        {ui.forbiddenBackHome}
      </Link>
    </main>
  );
}
